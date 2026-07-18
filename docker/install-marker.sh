#!/bin/bash
# 在已运行的 DocuLogic 容器中安装可选引擎 Marker（GPL-3.0）
# 用法（项目根目录）:
#   ./docker/install-marker.sh
#   ./docker/install-marker.sh doculogic
set -euo pipefail

CONTAINER="${1:-doculogic}"

echo "========================================="
echo "  安装可选引擎 Marker（marker-pdf）"
echo "========================================="
echo ""
echo "许可提示："
echo "  - 代码: GPL-3.0-or-later"
echo "  - 模型: OpenRAIL-M（及上游 surya 等条款）"
echo "  详见仓库 LICENSE-THIRD-PARTY.md"
echo ""
echo "注意：容器重建后需重新执行本脚本，或改用构建参数 INSTALL_MARKER=1。"
echo ""

if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER}"; then
  echo "❌ 容器未运行: ${CONTAINER}"
  echo "   请先: cd docker && docker compose up -d"
  exit 1
fi

if ! docker exec "${CONTAINER}" test -f /app/requirements-marker.txt; then
  echo "❌ 容器内缺少 /app/requirements-marker.txt，请更新镜像后重试"
  exit 1
fi

echo ">>> 正在容器 ${CONTAINER} 中 pip install ..."
docker exec "${CONTAINER}" pip install --no-cache-dir \
  -r /app/requirements-marker.txt

echo ""
echo ">>> 重启容器使插件生效 ..."
docker restart "${CONTAINER}"

echo ""
echo "✅ Marker 已安装。请到管理后台「解析器配置」→「切换解析器」选择 Marker。"
echo "   首次解析会自动下载 surya/Marker 模型到本机缓存。"
echo ""
