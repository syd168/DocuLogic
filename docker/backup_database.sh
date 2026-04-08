#!/bin/bash
# DocuLogic 数据库自动备份脚本（Docker 容器内版本）
# 
# 使用方法：
#   1. 手动执行：docker exec doculogic bash /app/backup_database.sh
#   2. 自动执行：cron 定时任务（每天凌晨 2 点）
#
# 备份文件将保存在 /app/backups 目录中，保留最近 7 天的备份

set -e

# 配置项
BACKUP_DIR="/app/backups"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
ENV_FILE="/app/.env"

# 颜色输出（如果支持）
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1" >&2
}

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 生成备份文件名
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/doculogic_backup_${TIMESTAMP}"

log_info "========================================="
log_info "开始备份数据库..."
log_info "========================================="

# 从 .env 文件读取配置
if [ -f "$ENV_FILE" ]; then
    DATABASE_TYPE=$(grep '^DATABASE_TYPE=' "$ENV_FILE" | cut -d'=' -f2 | tr -d '[:space:]')
else
    log_warn ".env 文件不存在，使用默认配置"
    DATABASE_TYPE="sqlite"
fi

# 如果未设置，默认为 sqlite
DATABASE_TYPE="${DATABASE_TYPE:-sqlite}"

log_info "数据库类型: $DATABASE_TYPE"
log_info "备份文件: $BACKUP_FILE"

if [ "$DATABASE_TYPE" = "mysql" ]; then
    # MySQL 备份（Docker 容器内）
    MYSQL_HOST="${MYSQL_HOST:-mysql}"
    MYSQL_PORT="${MYSQL_PORT:-3306}"
    MYSQL_USER="${MYSQL_USER:-root}"
    MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
    MYSQL_DATABASE="${MYSQL_DATABASE:-doculogic}"
    
    # 从 .env 读取密码（如果未设置环境变量）
    if [ -z "$MYSQL_PASSWORD" ] && [ -f "$ENV_FILE" ]; then
        MYSQL_PASSWORD=$(grep '^MYSQL_PASSWORD=' "$ENV_FILE" | cut -d'=' -f2 | tr -d '[:space:]')
    fi
    
    if [ -z "$MYSQL_PASSWORD" ]; then
        log_error "未找到 MySQL 密码配置"
        exit 1
    fi
    
    log_info "正在导出 MySQL 数据库..."
    
    # 使用 mysqldump 导出
    if command -v mysqldump &> /dev/null; then
        mysqldump \
            --host="$MYSQL_HOST" \
            --port="$MYSQL_PORT" \
            --user="$MYSQL_USER" \
            --password="$MYSQL_PASSWORD" \
            --single-transaction \
            --routines \
            --triggers \
            --events \
            "$MYSQL_DATABASE" | gzip > "${BACKUP_FILE}.sql.gz"
        
        if [ $? -eq 0 ]; then
            BACKUP_SIZE=$(du -h "${BACKUP_FILE}.sql.gz" | cut -f1)
            log_info "✅ MySQL 备份成功！文件大小: $BACKUP_SIZE"
        else
            log_error "❌ MySQL 备份失败"
            exit 1
        fi
    else
        log_error "未找到 mysqldump 命令，请先安装 mysql-client"
        exit 1
    fi
    
elif [ "$DATABASE_TYPE" = "sqlite" ]; then
    # SQLite 备份（Docker 容器内）
    DB_FILE="/app/web/data/app.db"
    
    if [ ! -f "$DB_FILE" ]; then
        log_error "SQLite 数据库文件不存在: $DB_FILE"
        exit 1
    fi
    
    log_info "正在复制 SQLite 数据库..."
    
    # 使用 sqlite3 的 .backup 命令（更安全）
    if command -v sqlite3 &> /dev/null; then
        sqlite3 "$DB_FILE" ".backup '${BACKUP_FILE}.db'"
        
        if [ $? -eq 0 ]; then
            # 压缩备份文件
            gzip "${BACKUP_FILE}.db"
            BACKUP_SIZE=$(du -h "${BACKUP_FILE}.db.gz" | cut -f1)
            log_info "✅ SQLite 备份成功！文件大小: $BACKUP_SIZE"
        else
            log_error "❌ SQLite 备份失败"
            exit 1
        fi
    else
        # 降级方案：直接复制文件
        log_warn "未找到 sqlite3 命令，使用文件复制方式..."
        cp "$DB_FILE" "${BACKUP_FILE}.db"
        gzip "${BACKUP_FILE}.db"
        BACKUP_SIZE=$(du -h "${BACKUP_FILE}.db.gz" | cut -f1)
        log_info "✅ SQLite 备份成功（文件复制）！文件大小: $BACKUP_SIZE"
    fi
else
    log_error "不支持的数据库类型: $DATABASE_TYPE"
    exit 1
fi

# 清理旧备份（保留最近 N 天）
log_info "清理 ${RETENTION_DAYS} 天前的旧备份..."
DELETED_COUNT=$(find "$BACKUP_DIR" -name "doculogic_backup_*.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)

if [ "$DELETED_COUNT" -gt 0 ]; then
    log_info "已删除 $DELETED_COUNT 个旧备份文件"
else
    log_info "没有需要清理的旧备份"
fi

# 显示备份统计
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "doculogic_backup_*.gz" | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

log_info "========================================="
log_info "备份统计："
log_info "  - 总备份数: $TOTAL_BACKUPS"
log_info "  - 总大小: $TOTAL_SIZE"
log_info "  - 保留天数: $RETENTION_DAYS"
log_info "========================================="

log_info "✅ 数据库备份完成！"

exit 0
