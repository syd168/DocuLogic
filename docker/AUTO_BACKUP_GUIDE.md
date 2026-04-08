# Docker 数据库自动备份使用说明

## 📋 概述

DocuLogic Docker 容器已内置**自动数据库备份功能**，每天凌晨 2 点自动执行备份。

## ✅ 已集成的功能

### 1. 自动定时备份
- **时间**：每天凌晨 2:00
- **位置**：`/app/backups` 容器内目录
- **保留**：默认保留最近 7 天的备份
- **格式**：gzip 压缩

### 2. 支持的数据库
- ✅ SQLite（默认）
- ✅ MySQL

### 3. 挂载到宿主机
在 `docker-compose.yml` 中已配置：
```yaml
volumes:
  - ${DATA_DIR:-~/doculogic/data}/backups:/app/backups
```

备份文件实际存储在宿主机的 `~/doculogic/data/backups/` 目录。

---

## 🚀 使用方法

### 方法 1：等待自动备份（推荐）

无需任何操作，系统会在每天凌晨 2 点自动备份。

### 方法 2：手动触发备份

```bash
# 进入 Docker 容器执行备份
docker exec doculogic bash /app/backup_database.sh
```

### 方法 3：修改备份频率

编辑 `docker/Dockerfile`，修改 cron 表达式：

```dockerfile
# 当前：每天凌晨 2 点
RUN echo "0 2 * * * cd /app && bash backup_database.sh >> /app/backups/backup.log 2>&1" > /etc/cron.d/doculogic-backup

# 改为：每 6 小时备份一次
RUN echo "0 */6 * * * cd /app && bash backup_database.sh >> /app/backups/backup.log 2>&1" > /etc/cron.d/doculogic-backup

# 改为：每周日凌晨 3 点
RUN echo "0 3 * * 0 cd /app && bash backup_database.sh >> /app/backups/backup.log 2>&1" > /etc/cron.d/doculogic-backup
```

然后重新构建镜像：
```bash
cd docker
docker compose down
docker compose build doculogic
docker compose up -d
```

### 方法 4：修改保留天数

在 `docker-compose.yml` 中添加环境变量：

```yaml
environment:
  - RETENTION_DAYS=30  # 保留 30 天
```

然后重启容器：
```bash
docker compose restart
```

---

## 📁 查看备份文件

### 在宿主机上查看

```bash
# 查看备份目录
ls -lh ~/doculogic/data/backups/

# 查看最近的备份
ls -lt ~/doculogic/data/backups/ | head -5

# 查看总大小
du -sh ~/doculogic/data/backups/
```

### 在容器内查看

```bash
docker exec doculogic ls -lh /app/backups/
```

---

## 🔄 恢复数据库

### SQLite 恢复

```bash
# 1. 停止服务
cd docker
docker compose down

# 2. 找到要恢复的备份文件
ls -lt ~/doculogic/data/backups/*.db.gz

# 3. 解压备份文件
gunzip ~/doculogic/data/backups/doculogic_backup_20260408_020000.db.gz

# 4. 替换数据库文件
cp ~/doculogic/data/backups/doculogic_backup_20260408_020000.db ~/doculogic/data/database/app.db

# 5. 启动服务
docker compose up -d
```

### MySQL 恢复

```bash
# 1. 停止服务
cd docker
docker compose down

# 2. 进入 MySQL 容器
docker exec -it doculogic-mysql bash

# 3. 从宿主机复制备份文件到容器
# （在另一个终端执行）
docker cp ~/doculogic/data/backups/doculogic_backup_20260408_020000.sql.gz doculogic-mysql:/tmp/restore.sql.gz

# 4. 在 MySQL 容器内恢复
docker exec -it doculogic-mysql bash
gunzip < /tmp/restore.sql.gz | mysql -uroot -p${MYSQL_PASSWORD} doculogic
exit

# 5. 启动服务
docker compose up -d
```

---

## 🔍 查看备份日志

```bash
# 查看备份日志
cat ~/doculogic/data/backups/backup.log

# 实时查看日志
tail -f ~/doculogic/data/backups/backup.log
```

---

## ⚙️ 高级配置

### 自定义备份目录

修改 `docker-compose.yml`：

```yaml
volumes:
  - /custom/backup/path:/app/backups
```

### 禁用自动备份

如果不需要自动备份，可以注释掉 Dockerfile 中的 cron 配置：

```dockerfile
# 注释掉这一行
# RUN echo "0 2 * * * ..." > /etc/cron.d/doculogic-backup
```

然后重新构建镜像。

### 测试备份脚本

```bash
# 手动执行一次备份，检查是否正常
docker exec doculogic bash /app/backup_database.sh

# 查看输出和日志
docker exec doculogic cat /app/backups/backup.log
```

---

## 🛡️ 安全建议

### 1. 异地备份

定期将备份文件同步到远程存储：

```bash
# 示例：同步到 NFS
rsync -avz ~/doculogic/data/backups/ /mnt/nfs/backups/

# 示例：同步到 S3（需要安装 aws-cli）
aws s3 sync ~/doculogic/data/backups/ s3://my-bucket/doculogic-backups/
```

### 2. 加密备份

对敏感数据进行加密：

```bash
# 使用 GPG 加密备份文件
gpg --symmetric --cipher-algo AES256 ~/doculogic/data/backups/doculogic_backup_*.gz
```

### 3. 监控告警

设置备份失败的告警（通过 cron 邮件或 webhook）。

---

## 🆘 故障排查

### 问题 1：备份未执行

**检查 cron 是否运行**：
```bash
docker exec doculogic ps aux | grep cron
```

**查看 cron 日志**：
```bash
docker exec doculogic cat /var/log/cron.log
```

### 问题 2：备份文件为空

**检查数据库文件是否存在**：
```bash
docker exec doculogic ls -lh /app/web/data/app.db
```

**手动执行备份查看详细错误**：
```bash
docker exec doculogic bash /app/backup_database.sh
```

### 问题 3：磁盘空间不足

**清理旧备份**：
```bash
# 删除 7 天前的备份
find ~/doculogic/data/backups/ -name "*.gz" -mtime +7 -delete
```

**调整保留天数**：
在 `docker-compose.yml` 中设置 `RETENTION_DAYS=3`。

---

## 📊 备份统计

```bash
# 查看备份数量和总大小
echo "备份数量: $(ls ~/doculogic/data/backups/*.gz 2>/dev/null | wc -l)"
echo "总大小: $(du -sh ~/doculogic/data/backups/ | cut -f1)"

# 查看最旧的备份
ls -lt ~/doculogic/data/backups/*.gz | tail -1

# 查看最新的备份
ls -lt ~/doculogic/data/backups/*.gz | head -1
```

---

## 💡 最佳实践

1. **定期测试恢复**：每月至少测试一次备份恢复流程
2. **监控磁盘空间**：确保备份目录有足够空间
3. **异地备份**：重要数据应同步到远程存储
4. **版本管理**：重大变更前手动备份一次
5. **日志审查**：定期检查备份日志，确保正常运行

---

## 📞 技术支持

如遇问题，请查看：
1. 备份日志：`~/doculogic/data/backups/backup.log`
2. 容器日志：`docker logs doculogic`
3. 项目文档：`README.md`
