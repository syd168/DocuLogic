#!/bin/bash
set -e

# DocuLogic Docker 一键部署脚本
echo "========================================="
echo "  DocuLogic 一键部署"
echo "========================================="
echo ""

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 切换到项目根目录
cd "${PROJECT_ROOT}"

# 配置
DATA_DIR="${DATA_DIR:-${HOME}/doculogic/data}"
MODEL_DIR="${MODEL_DIR:-${HOME}/doculogic/weights}"
HOST_PORT="${HOST_PORT:-8030}"

echo "📁 数据目录: ${DATA_DIR}"
echo "📦 模型目录: ${MODEL_DIR}"
echo "🌐 访问端口: ${HOST_PORT}"
echo ""

# 0. 检查 Docker 权限
echo "[0/7] 检查 Docker 权限..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行或无权限"
    echo "   请执行: sudo systemctl start docker"
    echo "   或将当前用户加入 docker 组: sudo usermod -aG docker $USER"
    exit 1
fi
echo "✓ Docker 运行正常"
echo ""

# 1. 检查并提示目录结构
echo "[1/5] 检查数据目录..."

# 仅检查根目录是否存在，不存在则创建
if [ ! -d "${DATA_DIR}" ]; then
    echo "⚠️  数据根目录不存在: ${DATA_DIR}"
    echo "   尝试创建..."
    mkdir -p "${DATA_DIR}" || {
        echo "❌ 无法创建目录，请手动执行:"
        echo "   sudo mkdir -p ${DATA_DIR}"
        echo "   sudo chown $(whoami):$(id -gn) ${DATA_DIR}"
        exit 1
    }
    echo "✓ 已创建: ${DATA_DIR}"
else
    echo "✓ 数据目录已存在: ${DATA_DIR}"
fi

# 检查子目录，如果不存在则提示（由 Docker 自动创建）
MISSING_DIRS=()
for dir in "${DATA_DIR}/output" "${DATA_DIR}/logs" "${DATA_DIR}/database/sqlite" "${DATA_DIR}/backups" "${MODEL_DIR}"; do
    if [ ! -d "$dir" ]; then
        MISSING_DIRS+=("$dir")
    fi
done

if [ ${#MISSING_DIRS[@]} -gt 0 ]; then
    echo "ℹ️  以下子目录将由 Docker 自动创建:"
    for dir in "${MISSING_DIRS[@]}"; do
        echo "   - $dir"
    done
    echo "   （Docker 会以 root 权限创建，首次启动后可能需要调整权限）"
fi

echo "✓ 目录结构检查完成"
echo ""

# 2. 检查本地转换器源码目录（不提交到 Git，需要用户提前准备）
echo "[2/7] 检查 converts/models 依赖目录..."
MODELS_DIR="${PROJECT_ROOT}/converts/models"
if [ ! -d "${MODELS_DIR}" ] || [ -z "$(ls -A "${MODELS_DIR}" 2>/dev/null)" ]; then
    echo "❌ 目录为空或不存在: ${MODELS_DIR}"
    echo ""
    echo "请先下载并放置至少一个转换器源码目录后再部署。"
    echo "说明：converts/models 已配置为不提交到 GitHub，需要部署方本地准备。"
    exit 1
fi
echo "✓ converts/models 依赖目录检查通过"
echo ""

# 3. 配置环境变量
echo "[3/7] 配置环境变量..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ 已创建 .env 文件"
    
    # 生成随机 JWT_SECRET
    if command -v python3 &> /dev/null; then
        JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        sed -i "s/JWT_SECRET=.*/JWT_SECRET=${JWT_SECRET}/" .env
        echo "✓ 已生成随机 JWT_SECRET"
    fi
else
    echo "✓ .env 文件已存在"
    
    # 检查 JWT_SECRET 是否仍为默认值
    CURRENT_JWT=$(grep -E '^JWT_SECRET=' .env | cut -d'=' -f2 | sed 's/#.*//' | tr -d '[:space:]' | tr -d '"' | tr -d "'")
    if [ "$CURRENT_JWT" = "change-me-in-production" ] || [ -z "$CURRENT_JWT" ]; then
        echo "⚠️  检测到 JWT_SECRET 为默认值或空，正在生成随机密钥..."
        if command -v python3 &> /dev/null; then
            JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
            sed -i "s/JWT_SECRET=.*/JWT_SECRET=${JWT_SECRET}/" .env
            echo "✓ 已生成新的随机 JWT_SECRET"
        else
            echo "❌ 无法生成随机密钥（需要 Python 3）"
            echo "   请手动修改 .env 文件中的 JWT_SECRET"
        fi
    else
        echo "✓ JWT_SECRET 已配置"
    fi
fi
echo ""

# 3.5. 数据迁移（如果切换到外部数据库）
echo "[3.5/7] 检查数据库迁移..."

# 读取 DATABASE_TYPE（去除注释和空格）
DATABASE_TYPE=$(grep -E '^DATABASE_TYPE=' .env | cut -d'=' -f2 | sed 's/#.*//' | tr -d '[:space:]' | tr -d '"' | tr -d "'")
DATABASE_TYPE=${DATABASE_TYPE:-sqlite}

# 获取数据目录
DATA_DIR="${DATA_DIR:-${HOME}/doculogic}"

echo ""
echo "⚠️  重要提示：切换数据库类型会导致数据隔离"
echo "   每种数据库类型使用独立的存储路径："
echo "   - SQLite:    ${DATA_DIR}/data/database/sqlite"
echo "   - MySQL:     ${DATA_DIR}/data/database/mysql"
echo "   - MariaDB:   ${DATA_DIR}/data/database/mariadb"
echo "   - PostgreSQL: ${DATA_DIR}/data/database/postgresql"
echo ""
echo "   如果您之前使用过其他数据库类型，需要先迁移数据！"
echo "   请使用 scripts/convert_sqlite_to_other.py 进行数据转换。"
echo ""

case "$DATABASE_TYPE" in
    mysql)
        echo "📊 检测到使用 MySQL 数据库"
        
        # 检查是否有其他数据库的数据
        if [ -d "${DATA_DIR}/data/database/sqlite" ] && [ -f "${DATA_DIR}/data/database/sqlite/app.db" ]; then
            echo "⚠️  发现 SQLite 数据库数据！"
            echo "   路径: ${DATA_DIR}/data/database/sqlite/app.db"
            echo ""
            echo "   如果不迁移数据，MySQL 将从空数据库开始，所有配置将丢失！"
            echo ""
            read -p "   是否现在从 SQLite 导出数据到 MySQL? [y/N]: " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "🔄 开始导出数据..."
                if python3 scripts/convert_sqlite_to_other.py export; then
                    echo "✅ 数据导出成功: web/data/mysql.sql"
                    echo "   Docker 启动后将自动导入到 MySQL"
                else
                    echo "❌ 数据导出失败"
                    exit 1
                fi
            else
                echo "⚠️  您选择了跳过迁移，MySQL 将从空数据库开始"
                echo "   如需稍后迁移，请运行: python3 scripts/convert_sqlite_to_other.py export"
            fi
        elif [ -d "${DATA_DIR}/data/database/mariadb" ]; then
            echo "⚠️  发现 MariaDB 数据目录，但当前选择的是 MySQL"
            echo "   这两个数据库不共享数据！"
        fi
        ;;
    
    mariadb)
        echo "📊 检测到使用 MariaDB 数据库"
        
        # 检查是否有其他数据库的数据
        if [ -d "${DATA_DIR}/data/database/sqlite" ] && [ -f "${DATA_DIR}/data/database/sqlite/app.db" ]; then
            echo "⚠️  发现 SQLite 数据库数据！"
            echo "   路径: ${DATA_DIR}/data/database/sqlite/app.db"
            echo ""
            echo "   如果不迁移数据，MariaDB 将从空数据库开始，所有配置将丢失！"
            echo ""
            read -p "   是否现在从 SQLite 导出数据到 MariaDB? [y/N]: " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "🔄 开始导出数据..."
                if python3 scripts/convert_sqlite_to_other.py export --output web/data/mariadb.sql; then
                    echo "✅ 数据导出成功: web/data/mariadb.sql"
                    echo "   Docker 启动后将自动导入到 MariaDB"
                else
                    echo "❌ 数据导出失败"
                    exit 1
                fi
            else
                echo "⚠️  您选择了跳过迁移，MariaDB 将从空数据库开始"
                echo "   如需稍后迁移，请运行: python3 scripts/convert_sqlite_to_other.py export --output web/data/mariadb.sql"
            fi
        elif [ -d "${DATA_DIR}/data/database/mysql" ]; then
            echo "⚠️  发现 MySQL 数据目录，但当前选择的是 MariaDB"
            echo "   这两个数据库不共享数据！"
        fi
        ;;
    
    postgresql|postgres|pg)
        echo "ℹ️  检测到使用 PostgreSQL 数据库"
        
        POSTGRESQL_SQL="web/data/postgresql.sql"
        if [ -f "$POSTGRESQL_SQL" ]; then
            echo "✅ 找到 PostgreSQL 初始化文件: $POSTGRESQL_SQL"
            echo "   Docker 启动后将自动导入数据"
        else
            echo "⚠️  未找到 PostgreSQL 初始化文件"
            echo "   请确保 web/data/postgresql.sql 存在"
        fi
        ;;
    
    sqlite)
        echo "✓ 使用 SQLite 数据库，无需迁移"
        ;;
    
    *)
        echo "⚠️  未知的数据库类型: $DATABASE_TYPE"
        ;;
esac

echo ""

# 4. 停止旧服务并清理其他数据库容器
echo "[4/7] 检查并停止旧服务..."
cd docker

# 4.1 停止当前配置的服务
echo "🔄 停止当前配置的服务..."
if docker compose ps --services 2>/dev/null | grep -q .; then
    docker compose down
    echo "✓ 当前服务已停止"
else
    echo "✓ 没有运行中的服务"
fi

# 4.2 清理其他数据库类型的容器（防止切换数据库类型后残留）
echo "🧹 清理可能存在的其他数据库容器..."
DB_CONTAINERS_TO_REMOVE=()

case "$DATABASE_TYPE" in
    mysql)
        # 如果使用 MySQL，清理 MariaDB 和 PostgreSQL 容器
        DB_CONTAINERS_TO_REMOVE=("doculogic-mariadb" "doculogic-postgresql")
        ;;
    mariadb)
        # 如果使用 MariaDB，清理 MySQL 和 PostgreSQL 容器
        DB_CONTAINERS_TO_REMOVE=("doculogic-mysql" "doculogic-postgresql")
        ;;
    postgresql|postgres|pg)
        # 如果使用 PostgreSQL，清理 MySQL 和 MariaDB 容器
        DB_CONTAINERS_TO_REMOVE=("doculogic-mysql" "doculogic-mariadb")
        ;;
    sqlite)
        # 如果使用 SQLite，清理所有数据库容器（保留 Redis）
        DB_CONTAINERS_TO_REMOVE=("doculogic-mysql" "doculogic-mariadb" "doculogic-postgresql")
        ;;
esac

# 检查并移除容器
REMOVED_COUNT=0
for container_name in "${DB_CONTAINERS_TO_REMOVE[@]}"; do
    if docker ps -a --format '{{.Names}}' | grep -q "^${container_name}$"; then
        echo "   🗑️  发现残留容器: ${container_name}，正在移除..."
        docker rm -f "${container_name}" > /dev/null 2>&1
        REMOVED_COUNT=$((REMOVED_COUNT + 1))
    fi
done

if [ $REMOVED_COUNT -gt 0 ]; then
    echo "✓ 已清理 ${REMOVED_COUNT} 个残留容器"
else
    echo "✓ 无需清理的残留容器"
fi

cd ..
echo ""

# 5. 构建镜像
echo "[5/7] 构建 Docker 镜像..."
cd docker
docker compose build
cd ..
echo "✓ 镜像构建完成"
echo ""

# 6. 启动服务
echo "[6/7] 启动服务..."

# 安全加载 .env 文件（处理特殊字符）
if [ -f .env ]; then
    # 逐行读取并导出变量，避免特殊字符问题
    while IFS= read -r line; do
        # 跳过注释和空行
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$(echo "$line" | tr -d '[:space:]')" ]] && continue
        
        # 提取键值对（去除行尾注释）
        key=$(echo "$line" | cut -d'=' -f1 | tr -d '[:space:]')
        value=$(echo "$line" | cut -d'=' -f2- | sed 's/#.*//' | sed 's/^["'\'']*//;s/["'\'']*$//' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        # 跳过无效行
        [[ -z "$key" ]] && continue
        
        # 导出变量
        export "$key"="$value"
    done < .env
fi

# 确保关键变量已设置
export DATA_DIR="${DATA_DIR:-${HOME}/doculogic}"
export MODEL_DIR="${MODEL_DIR:-${DATA_DIR}/weights}"
export HOST_PORT="${HOST_PORT:-8030}"
export DATABASE_TYPE="${DATABASE_TYPE:-sqlite}"

# 🎯 根据 DATABASE_TYPE 自动选择 Docker Compose profiles
COMPOSE_PROFILES=""
case "$DATABASE_TYPE" in
    mysql)
        COMPOSE_PROFILES="mysql"
        echo "📊 检测到使用 MySQL 数据库，启用 MySQL 服务"
        ;;
    mariadb)
        COMPOSE_PROFILES="mariadb"
        echo "📊 检测到使用 MariaDB 数据库，启用 MariaDB 服务"
        ;;
    postgresql|postgres|pg)
        COMPOSE_PROFILES="postgresql"
        echo "📊 检测到使用 PostgreSQL 数据库，启用 PostgreSQL 服务"
        ;;
    sqlite)
        COMPOSE_PROFILES=""
        echo "📊 使用 SQLite 数据库，无需额外数据库服务"
        ;;
    *)
        echo "⚠️  未知的数据库类型: $DATABASE_TYPE，默认使用 SQLite"
        COMPOSE_PROFILES=""
        ;;
esac

cd docker
if [ -n "$COMPOSE_PROFILES" ]; then
    # 使用指定的 profile 启动
    echo "🚀 启动命令: docker compose --profile $COMPOSE_PROFILES up -d"
    docker compose --profile "$COMPOSE_PROFILES" up -d
else
    # 不使用 profile（SQLite 模式）
    echo "🚀 启动命令: docker compose up -d"
    docker compose up -d
fi

echo "✓ 服务已启动"
echo ""

# 7. 验证部署
echo "[7/7] 验证部署..."
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
echo "  ├── output/          # 文档解析输出文件"
echo "  ├── logs/            # 应用日志文件"
echo "  │   └── app.log"
echo "  ├── database/        # 数据库文件目录"
echo "  │   ├── sqlite/      # SQLite 数据库 (DATABASE_TYPE=sqlite)"
echo "  │   ├── mysql/       # MySQL 数据 (DATABASE_TYPE=mysql)"
echo "  │   ├── mariadb/     # MariaDB 数据 (DATABASE_TYPE=mariadb)"
echo "  │   └── postgresql/  # PostgreSQL 数据 (DATABASE_TYPE=postgresql)"
echo "  ├── redis/           # Redis 缓存数据"
echo "  └── backups/         # 数据库备份文件"
echo ""
echo "模型目录: ${MODEL_DIR}/"
echo ""
echo "服务列表:"
echo "  - doculogic      # 主应用（FastAPI + Nginx）"
echo "  - redis          # Redis缓存服务"

# 根据 DATABASE_TYPE 显示对应的数据库服务
case "$DATABASE_TYPE" in
    mysql)
        echo "  - mysql          # MySQL 数据库"
        ;;
    mariadb)
        echo "  - mariadb        # MariaDB 数据库"
        ;;
    postgresql|postgres|pg)
        echo "  - postgresql     # PostgreSQL 数据库"
        ;;
    sqlite)
        echo "  ℹ️  使用 SQLite，无独立数据库服务"
        ;;
esac
echo ""
echo "常用命令:"
echo "  查看日志:   cd docker && docker compose logs -f"
echo "  停止服务:   cd docker && docker compose down"
echo "  重启服务:   cd docker && docker compose restart"
echo "  进入容器:   docker exec -it doculogic bash"
echo "  Redis CLI:  docker exec -it doculogic-redis redis-cli"

# 根据 DATABASE_TYPE 显示对应的数据库管理命令
case "$DATABASE_TYPE" in
    mysql)
        echo "  MySQL CLI:      docker exec -it doculogic-mysql mysql -uroot -p"
        echo "  MySQL Backup:   docker exec doculogic-mysql mysqldump -uroot -p doculogic > backup.sql"
        ;;
    mariadb)
        echo "  MariaDB CLI:    docker exec -it doculogic-mariadb mariadb -uroot -p"
        echo "  MariaDB Backup: docker exec doculogic-mariadb mariadb-dump -uroot -p doculogic > backup.sql"
        ;;
    postgresql|postgres|pg)
        echo "  PostgreSQL CLI: docker exec -it doculogic-postgresql psql -U postgres -d doculogic"
        echo "  PG Backup:      docker exec doculogic-postgresql pg_dump -U postgres doculogic > backup.sql"
        ;;
esac
echo ""
echo "默认管理员账号:"
echo "  用户名: admin"
echo "  密码:   admin123"
echo "  ⚠️  请立即修改密码！"
echo ""
