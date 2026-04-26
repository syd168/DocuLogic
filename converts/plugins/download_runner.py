from __future__ import annotations

import logging
import os
import re
import shlex
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import json

from converts.middleware.contracts import (
    ConverterDownloadRequest,
    ConverterDownloadSchema,
    ConverterDownloadStatus,
)

_log = logging.getLogger(__name__)


def _dir_size_bytes(path: Path) -> int:
    if not path.exists() or not path.is_dir():
        return 0
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                continue
    return total


def _strip_jsonc_comments(text: str) -> str:
    no_block = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    out: list[str] = []
    for line in no_block.splitlines():
        in_str = False
        escaped = False
        cut_at = None
        for i, ch in enumerate(line):
            if escaped:
                escaped = False
                continue
            if ch == "\\" and in_str:
                escaped = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if not in_str and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                cut_at = i
                break
        out.append((line[:cut_at] if cut_at is not None else line).rstrip())
    return "\n".join(out)


def _read_download_config_from_jsonc(engine_id: str) -> dict:
    path = Path.cwd() / "converts" / "configs" / f"{engine_id}.jsonc"
    if not path.exists():
        return {}
    try:
        raw = _strip_jsonc_comments(path.read_text(encoding="utf-8")).strip()
        if not raw:
            return {}
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        download = data.get("download") or {}
        return download if isinstance(download, dict) else {}
    except Exception:
        return {}


def _get_stall_timeout_seconds() -> int:
    """下载长时间无进度判定阈值（秒）。"""
    raw = str(os.environ.get("DOWNLOAD_STALL_TIMEOUT_SECONDS", "180")).strip()
    try:
        return max(30, int(raw))
    except Exception:
        return 180


class PluginDownloadRunner:
    def __init__(
        self,
        *,
        engine_id: str,
        default_source: str,
        allowed_sources: list[str],
        repos: dict[str, str],
        target_dir: str,
        notes: str = "",
        fallback_source: dict[str, str] | None = None,
    ) -> None:
        self.engine_id = engine_id
        self.default_source = default_source
        self.allowed_sources = allowed_sources
        self.repos = repos
        self.target_dir = target_dir
        self.notes = notes
        self.fallback_source = fallback_source or {}
        self._lock = threading.Lock()
        self._statuses: dict[str, ConverterDownloadStatus] = {}
        self._tasks: dict[str, dict] = {}

    def _dest_path_from_download_cfg(self, dcfg: dict, override: str) -> Path:
        """与 start() 一致：override → JSONC download.dest_dir → 插件默认。"""
        cfg_dest = str(dcfg.get("dest_dir") or "").strip()
        target_dir = (override or "").strip() or cfg_dest or self.target_dir
        if not target_dir:
            raise RuntimeError("未配置下载目标路径")
        dest = Path(target_dir)
        if not dest.is_absolute():
            dest = Path.cwd() / dest
        return dest

    def get_schema(self) -> ConverterDownloadSchema:
        return ConverterDownloadSchema(
            engine_id=self.engine_id,
            supports_download=True,
            default_source=self.default_source,
            allowed_sources=list(self.allowed_sources),
            default_repo_by_source=dict(self.repos),
            default_target_dir=self.target_dir,
            supports_repo_override=True,
            supports_target_override=True,
            notes=self.notes,
        )

    def start(self, request: ConverterDownloadRequest) -> ConverterDownloadStatus:
        dcfg = _read_download_config_from_jsonc(self.engine_id)
        cfg_mode = str(dcfg.get("mode") or "snapshot").strip().lower()
        cfg_sources = dcfg.get("repos") if isinstance(dcfg.get("repos"), dict) else {}
        source = (request.source or self.default_source).strip()
        if source not in self.allowed_sources:
            raise RuntimeError(f"不支持的下载源: {source}")
        repo = (
            (request.repo_id or "").strip()
            or str(cfg_sources.get(source) or "").strip()
            or (self.repos.get(source) or "").strip()
        )
        if not repo:
            raise RuntimeError(f"未配置 {source} 仓库")
        dest = self._dest_path_from_download_cfg(dcfg, request.target_dir or "")

        task_id = uuid4().hex
        status = ConverterDownloadStatus(
            task_id=task_id,
            engine_id=self.engine_id,
            is_downloading=True,
            success=False,
            message=f"正在下载 {self.engine_id} ...",
            source=source,
            repo=repo,
            dest=str(dest),
        )
        with self._lock:
            self._statuses[task_id] = status
            self._tasks[task_id] = {"cancelled": False, "proc": None}
        _log.info(
            "[download] start engine=%s task=%s source=%s repo=%s dest=%s mode=%s",
            self.engine_id,
            task_id,
            source,
            repo,
            str(dest),
            cfg_mode,
        )

        threading.Thread(
            target=self._run_task,
            args=(
                task_id,
                source,
                repo,
                dest,
                {"mode": cfg_mode, **(request.extras or {})},
            ),
            daemon=True,
        ).start()
        return status

    def status(self, task_id: str) -> ConverterDownloadStatus:
        with self._lock:
            s = self._statuses.get(task_id)
            if s is None:
                raise RuntimeError(f"下载任务不存在: {task_id}")
            return s

    def stop(self, task_id: str) -> ConverterDownloadStatus:
        with self._lock:
            s = self._statuses.get(task_id)
            if s is None:
                raise RuntimeError(f"下载任务不存在: {task_id}")
            if not s.is_downloading:
                return s
            task = self._tasks.get(task_id) or {}
            task["cancelled"] = True
            proc = task.get("proc")
        if proc is not None and proc.poll() is None:
            proc.terminate()
            time.sleep(0.2)
            if proc.poll() is None:
                proc.kill()
        self._set_status(
            task_id,
            lambda cur: ConverterDownloadStatus(
                **{
                    **cur.__dict__,
                    "is_downloading": False,
                    "success": False,
                    "error": "用户停止下载",
                    "message": "下载已停止",
                }
            ),
        )
        _log.info("[download] stopped engine=%s task=%s", self.engine_id, task_id)
        return self.status(task_id)

    def clear_files(self, target_dir: str = "") -> dict:
        dcfg = _read_download_config_from_jsonc(self.engine_id)
        path = self._dest_path_from_download_cfg(dcfg, target_dir or "")
        with self._lock:
            if any(s.is_downloading for s in self._statuses.values()):
                raise RuntimeError("存在进行中的下载任务，无法删除模型文件")
        if not path.exists():
            return {"ok": True, "deleted": False, "path": str(path), "message": "目录不存在，无需删除"}
        if not path.is_dir():
            raise RuntimeError(f"目标不是目录: {path}")
        rmtree(path)
        return {"ok": True, "deleted": True, "path": str(path), "message": "模型文件目录已删除"}

    def _set_status(self, task_id: str, updater) -> None:
        with self._lock:
            cur = self._statuses.get(task_id)
            if cur is None:
                return
            self._statuses[task_id] = updater(cur)

    def _run_task(self, task_id: str, source: str, repo: str, dest: Path, extras: dict) -> None:
        try:
            mode = str(extras.get("mode") or "snapshot").strip().lower()
            _log.info(
                "[download] running engine=%s task=%s mode=%s source=%s repo=%s dest=%s",
                self.engine_id,
                task_id,
                mode,
                source,
                repo,
                str(dest),
            )
            if mode == "command":
                cmd = str(extras.get("command") or "").strip()
                if not cmd:
                    raise RuntimeError("mode=command 时必须提供 command")
                self._run_external_command(task_id, shlex.split(cmd))
                self._set_status(
                    task_id,
                    lambda cur: ConverterDownloadStatus(
                        **{**cur.__dict__, "is_downloading": False, "success": True, "message": "下载完成"}
                    ),
                )
                return

            try:
                self._run_snapshot_download(task_id, source, repo, dest)
            except Exception as first_err:
                fallback = self.fallback_source.get(source)
                if not fallback:
                    raise
                fallback_repo = (self.repos.get(fallback) or "").strip()
                if not fallback_repo:
                    raise
                _log.warning(
                    "[download] fallback engine=%s task=%s from=%s to=%s reason=%s",
                    self.engine_id,
                    task_id,
                    source,
                    fallback,
                    str(first_err),
                )
                self._run_snapshot_download(task_id, fallback, fallback_repo, dest)
                source = fallback
                repo = fallback_repo
                self._set_status(
                    task_id,
                    lambda cur: ConverterDownloadStatus(
                        **{
                            **cur.__dict__,
                            "source": source,
                            "repo": repo,
                            "message": f"下载完成（{first_err}; 已自动回退到 {fallback}）",
                        }
                    ),
                )

            self._set_status(
                task_id,
                lambda cur: ConverterDownloadStatus(
                    **{
                        **cur.__dict__,
                        "is_downloading": False,
                        "success": True,
                        "source": source,
                        "repo": repo,
                        "message": "下载完成",
                    }
                ),
            )
            _log.info(
                "[download] success engine=%s task=%s source=%s repo=%s dest=%s",
                self.engine_id,
                task_id,
                source,
                repo,
                str(dest),
            )
        except Exception as e:
            _log.error(
                "[download] failed engine=%s task=%s error=%s",
                self.engine_id,
                task_id,
                str(e),
            )
            self._set_status(
                task_id,
                lambda cur: ConverterDownloadStatus(
                    **{
                        **cur.__dict__,
                        "is_downloading": False,
                        "success": False,
                        "error": str(e),
                        "message": f"下载失败: {str(e)[:300]}",
                    }
                ),
            )
        finally:
            with self._lock:
                task = self._tasks.get(task_id)
                if task:
                    task["proc"] = None

    def _run_snapshot_download(self, task_id: str, source: str, repo: str, dest: Path) -> None:
        code = (
            "import sys\n"
            "from pathlib import Path\n"
            "source, repo, dest = sys.argv[1], sys.argv[2], sys.argv[3]\n"
            "Path(dest).mkdir(parents=True, exist_ok=True)\n"
            "if source == 'huggingface':\n"
            "    from huggingface_hub import snapshot_download\n"
            "    snapshot_download(repo_id=repo, local_dir=dest, local_dir_use_symlinks=False, resume_download=True)\n"
            "elif source == 'modelscope':\n"
            "    from modelscope import snapshot_download\n"
            "    snapshot_download(repo_id=repo, local_dir=dest)\n"
            "else:\n"
            "    raise RuntimeError(f'unsupported source: {source}')\n"
        )
        if source == "huggingface":
            # 先走默认端点；失败后自动尝试镜像端点，提升国内网络可用性。
            endpoints = [os.environ.get("HF_ENDPOINT", "").strip(), "https://hf-mirror.com"]
            attempted = set()
            last_error: Exception | None = None
            for endpoint in endpoints:
                ep = endpoint or ""
                if ep in attempted:
                    continue
                attempted.add(ep)
                env_overrides = {}
                if ep:
                    env_overrides["HF_ENDPOINT"] = ep
                try:
                    self._run_external_command(
                        task_id,
                        [sys.executable, "-c", code, source, repo, str(dest)],
                        env_overrides=env_overrides,
                    )
                    if ep:
                        self._set_status(
                            task_id,
                            lambda cur: ConverterDownloadStatus(
                                **{**cur.__dict__, "message": f"下载中（使用镜像端点: {ep}）"}
                            ),
                        )
                    return
                except Exception as e:
                    last_error = e
                    continue
            raise RuntimeError(f"HuggingFace 下载失败（已尝试默认端点和镜像）: {last_error}")

        self._run_external_command(task_id, [sys.executable, "-c", code, source, repo, str(dest)])

    def _run_external_command(self, task_id: str, cmd: list[str], env_overrides: dict | None = None) -> None:
        env = os.environ.copy()
        if env_overrides:
            env.update({str(k): str(v) for k, v in env_overrides.items()})
        proc = subprocess.Popen(
            cmd,
            cwd=str(Path.cwd()),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        _log.info(
            "[download] spawn engine=%s task=%s pid=%s cmd=%s",
            self.engine_id,
            task_id,
            proc.pid,
            " ".join(cmd),
        )
        # 持续抽干子进程输出，避免 PIPE 写满导致下载进程卡死。
        out_lines: deque[str] = deque(maxlen=200)
        err_lines: deque[str] = deque(maxlen=200)

        def _drain_stream(stream, bucket: deque[str]) -> None:
            if stream is None:
                return
            try:
                for line in iter(stream.readline, ""):
                    if not line:
                        break
                    bucket.append(line.rstrip("\n"))
            except Exception:
                return

        t_out = threading.Thread(target=_drain_stream, args=(proc.stdout, out_lines), daemon=True)
        t_err = threading.Thread(target=_drain_stream, args=(proc.stderr, err_lines), daemon=True)
        t_out.start()
        t_err.start()

        with self._lock:
            task = self._tasks.get(task_id) or {}
            task["proc"] = proc
            self._tasks[task_id] = task
            cur = self._statuses.get(task_id)
            dest_path = Path(cur.dest) if cur and cur.dest else None
        start_ts = time.time()
        stall_timeout = _get_stall_timeout_seconds()
        last_report = 0.0
        last_log_heartbeat = 0.0
        last_size = _dir_size_bytes(dest_path) if dest_path else 0
        stagnant_since = start_ts
        while proc.poll() is None:
            with self._lock:
                cancelled = bool((self._tasks.get(task_id) or {}).get("cancelled"))
            if cancelled:
                proc.terminate()
                time.sleep(0.2)
                if proc.poll() is None:
                    proc.kill()
                raise RuntimeError("用户停止下载")
            now = time.time()
            if now - last_report >= 2.0:
                current_size = _dir_size_bytes(dest_path) if dest_path else 0
                if current_size > last_size:
                    stagnant_since = now
                stagnant_sec = int(max(0, now - stagnant_since))
                elapsed_sec = int(now - start_ts)
                if stagnant_sec >= stall_timeout:
                    proc.terminate()
                    time.sleep(0.2)
                    if proc.poll() is None:
                        proc.kill()
                    raise RuntimeError(
                        f"下载长时间无进度（{stagnant_sec}s）。可能网络中断、源站不可达或进程异常，请重试。"
                    )
                if now - last_log_heartbeat >= 10.0:
                    _log.info(
                        "[download] heartbeat engine=%s task=%s pid=%s elapsed=%ss size_mb=%.2f stagnant=%ss",
                        self.engine_id,
                        task_id,
                        proc.pid,
                        elapsed_sec,
                        current_size / (1024 * 1024),
                        stagnant_sec,
                    )
                    last_log_heartbeat = now
                self._set_status(
                    task_id,
                    lambda cur: ConverterDownloadStatus(
                        **{
                            **cur.__dict__,
                            "message": (
                                f"下载中（已用时 {elapsed_sec}s，已下载约 {current_size / (1024 * 1024):.2f} MB）"
                                + ("，当前网络响应较慢，请耐心等待" if stagnant_sec >= 20 else "")
                            ),
                        }
                    ),
                )
                last_size = current_size
                last_report = now
            time.sleep(0.2)
        t_out.join(timeout=1.0)
        t_err.join(timeout=1.0)
        out = "\n".join(out_lines)
        err = "\n".join(err_lines)
        if proc.returncode != 0:
            detail = (err or out or "").strip()
            raise RuntimeError(f"下载失败（exit={proc.returncode}）：{detail[:500]}")
        _log.info(
            "[download] process-exit-ok engine=%s task=%s pid=%s",
            self.engine_id,
            task_id,
            proc.pid,
        )
