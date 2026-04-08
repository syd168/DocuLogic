#!/bin/bash
set -e

# DocuLogic Docker 一键部署脚本
echo "========================================="
echo "  DocuLogic 一键部署"
echo "========================================="
echo ""

# 配置
DATA_DIR="${DATA_DIR:-${HOME}/doculogic}"
MODEL_DIR="${MODEL_DIR:-${DATA_DIR}/models}"
HOST_PORT="${HOST_PORT:-8030}"

echo "📁 数据目录: ${DATA_DIR}"
echo "📦 模型目录: ${MODEL_DIR}"
echo "🌐 访问端口: ${HOST_PORT}"
echo ""

# 0. 检查 Docker 权限
echo "[0/6] 检查 Docker 权限..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行或无权限"
    echo "   请执行: sudo systemctl start docker"
    echo "   或将当前用户加入 docker 组: sudo usermod -aG docker $USER"
    exit 1
fi
echo "✓ Docker 运行正常"
echo ""

# 1. 创建目录结构
echo "[1/5] 检查并创建目录结构..."

# 检查目录是否存在且有写权限
for dir in "${DATA_DIR}/output" "${DATA_DIR}/logs" "${DATA_DIR}/database" "${MODEL_DIR}"; do
    if [ -d "$dir" ]; then
        # 目录已存在，检查写权限
        if [ ! -w "$dir" ]; then
            echo "⚠️  警告: 目录 $dir 存在但无写权限"
            echo "   尝试修复权限..."
            chmod -R 755 "$dir" 2>/dev/null || {
                echo "❌ 无法修复权限，请手动执行:"
                echo "   sudo chown -R $(whoami):$(id -gn) ${DATA_DIR}"
                echo "   sudo chmod -R 755 ${DATA_DIR}"
                exit 1
            }
            echo "✓ 权限已修复"
        else
            echo "✓ 目录已存在: $dir"
        fi
    else
        # 目录不存在，创建它
        mkdir -p "$dir" || {
            echo "❌ 无法创建目录: $dir"
            echo "   请检查父目录权限或手动创建:"
            echo "   mkdir -p $dir"
            exit 1
        }
        echo "✓ 已创建目录: $dir"
    fi
done

echo "✓ 目录结构检查完成"
echo ""

# 2. 检查模型
echo "[2/6] 检查模型文件..."
if [ -f "${MODEL_DIR}/config.json" ] || [ -d "${MODEL_DIR}/Logics-Parsing-v2" ]; then
    echo "✓ 模型文件已存在"
else
    echo "⚠️  模型文件不存在"
    echo ""
    echo "请下载模型到: ${MODEL_DIR}"
    echo "  方式1: python logics-parsingv2/download_model_v2.py"
    echo "  方式2: 手动下载后移动到 ${MODEL_DIR}"
    echo ""
    read -p "是否继续部署？(可以稍后下载模型) [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    export ALLOW_START_WITHOUT_MODEL=1
fi
echo ""

# 3. 配置环境变量
echo "[3/6] 配置环境变量..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ 已创建 .env 文件"
    
    # 生成随机 JWT_SECRET
    if command -v python3 &> /dev/null; then
        JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        sed -i "s/JWT_SECRET=.*/JWT_SECRET=${JWT_SECRET}/" .env
    fi
else
    echo "✓ .env 文件已存在"
fi
echo ""

# 4. 构建镜像
echo "[4/6] 构建 Docker 镜像..."
cd docker
docker compose build
cd ..
echo "✓ 镜像构建完成"
echo ""

# 5. 启动服务
echo "[5/6] 启动服务..."
export DATA_DIR="${DATA_DIR}"
export MODEL_DIR="${MODEL_DIR}"
export HOST_PORT="${HOST_PORT}"

cd docker
docker compose up -d
cd ..

echo "✓ 服务已启动"
echo ""

# 6. 验证部署
echo "[6/6] 验证部署..."
echo "等待服务启动..."
sleep 5

# 健康检查
if curl -s http://localhost:${HOST_PORT}/health > /dev/null 2>&1; then
    echo "✅ 服务运行正常"
else
    echo "⚠️  服务可能还在启动中，请稍后访问"
    echo "查看日志: cd docker && docker compose logs -f"
fi

echo ""
echo "========================================="
echo "  ✅ 部署完成！"
echo "========================================="
echo ""
echo "访问地址: http://localhost:${HOST_PORT}"
echo "API 文档: http://localhost:${HOST_PORT}/api/docs"
echo ""
echo "数据目录: ${DATA_DIR}/"
echo "  ├── output/      # 解析输出"
echo "  ├── logs/        # 日志文件"
echo "  ├── database/    # 数据库"
echo "  └── models/      # 模型权重"
echo ""
echo "常用命令:"
echo "  查看日志:   cd docker && docker compose logs -f"
echo "  停止服务:   cd docker && docker compose down"
echo "  重启服务:   cd docker && docker compose restart"
echo "  进入容器:   docker exec -it doculogic bash"
echo ""
echo "默认管理员账号:"
echo "  用户名: admin"
echo "  密码:   admin123"
echo "  ⚠️  请立即修改密码！"
echo ""
