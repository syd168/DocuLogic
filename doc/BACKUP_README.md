# 数据库备份使用说明

## 📋 概述

DocuLogic 提供了自动化的数据库备份脚本，支持 SQLite 和 MySQL 两种数据库。

## 🚀 快速开始

### 1. 手动备份

```bash
cd scripts
bash backup_database.sh
```

### 2. 定时自动备份（推荐）

编辑 crontab：
```bash
crontab -e
```

添加以下行（每天凌晨 2 点执行备份）：
```cron
0 2 * * * cd /path/to/DocuLogic/scripts && bash backup_database.sh >> backups/backup.log 2>&1
```

## ⚙️ 配置选项

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `BACKUP_DIR` | 备份文件存储目录 | `./backups` |
| `RETENTION_DAYS` | 备份保留天数 | `7` |
| `DATABASE_TYPE` | 数据库类型（自动从 .env 读取） | `sqlite` |

### 示例：自定义配置

```bash
# 保留 30 天备份，存储到指定目录
BACKUP_DIR=/data/backups RETENTION_DAYS=30 bash backup_database.sh
```

## 📁 备份文件结构

```
backups/
├── doculogic_backup_20260408_020000.sql.gz  # MySQL 备份
├── doculogic_backup_20260409_020000.db.gz   # SQLite 备份
├── doculogic_backup_20260410_020000.sql.gz
└── backup.log                                # 备份日志
```

## 🔄 恢复数据库

### SQLite 恢复

```bash
# 1. 停止服务
docker compose down

# 2. 解压备份文件
gunzip backups/doculogic_backup_20260408_020000.db.gz

# 3. 替换数据库文件
cp backups/doculogic_backup_20260408_020000.db ~/doculogic/data/database/app.db

# 4. 启动服务
docker compose up -d
```

### MySQL 恢复

```bash
# 1. 停止服务
docker compose down

# 2. 进入 MySQL 容器
docker exec -it doculogic-mysql bash

# 3. 恢复数据库
gunzip < /app/backups/doculogic_backup_20260408_020000.sql.gz | \
  mysql -uroot -p${MYSQL_PASSWORD} doculogic

# 4. 退出并重启
exit
docker compose up -d
```

## 🔍 查看备份统计

```bash
# 查看备份文件列表
ls -lh backups/

# 查看总大小
du -sh backups/

# 查看最近的备份
ls -lt backups/ | head -5
```

## ⚠️ 注意事项

1. **首次使用前**：确保 `.env` 文件中配置了正确的数据库信息
2. **磁盘空间**：定期检查备份目录大小，避免占满磁盘
3. **异地备份**：建议将备份文件同步到远程存储（如 NFS、S3）
4. **测试恢复**：定期测试备份文件的恢复流程，确保可用性
5. **权限设置**：备份脚本需要读写数据库文件的权限

## 🛡️ 安全建议

1. **加密备份**：对敏感数据，建议使用 GPG 加密备份文件
2. **访问控制**：限制备份目录的访问权限
   ```bash
   chmod 700 backups/
   ```
3. **监控告警**：设置备份失败的告警通知

## 📊 备份策略建议

| 场景 | 频率 | 保留时间 | 存储位置 |
|------|------|----------|----------|
| 开发环境 | 每周 | 7 天 | 本地 |
| 测试环境 | 每天 | 14 天 | 本地 + NAS |
| 生产环境 | 每天 | 30 天 | 本地 + 云存储 |
| 关键业务 | 每小时 | 7 天 | 多地冗余 |

## 🆘 故障排查

### 问题 1：备份失败，提示 "Permission denied"

**解决方案**：
```bash
chmod +x backup_database.sh
chown -R $USER:$USER backups/
```

### 问题 2：mysqldump 命令未找到

**解决方案**：
```bash
# Ubuntu/Debian
sudo apt-get install mysql-client

# CentOS/RHEL
sudo yum install mysql
```

### 问题 3：备份文件过大

**解决方案**：
- 检查是否有不必要的大表数据
- 考虑增量备份方案
- 增加压缩级别：`gzip -9`

## 📞 技术支持

如遇问题，请查看：
1. 备份日志：`backups/backup.log`
2. 系统日志：`docker logs doculogic`
3. 项目文档：`../README.md`
