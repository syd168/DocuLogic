"""任务级取消：后台线程中检查 threading.Event，用于 PDF 分页之间协作停止。"""
import threading
from typing import Dict, Optional

_events: Dict[str, threading.Event] = {}


def register_job(job_id: str) -> threading.Event:
    ev = threading.Event()
    _events[job_id] = ev
    return ev


def get_event(job_id: str) -> Optional[threading.Event]:
    return _events.get(job_id)


def cancel_job(job_id: str) -> bool:
    ev = _events.get(job_id)
    if ev:
        ev.set()
        return True
    return False


def remove_job(job_id: str) -> None:
    _events.pop(job_id, None)


def is_job_running(job_id: str) -> bool:
    """检查任务是否仍在运行（在 cancel_events 中）"""
    return job_id in _events
