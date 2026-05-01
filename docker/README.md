# DocuLogic Docker 部署指南

<div align="center">

**🚀 容器化部署与运维补充说明**

[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![GPU](https://img.shields.io/badge/GPU-Supported-green.svg)](https://developer.nvidia.com/cuda-zone)
[![Redis](https://img.shields.io/badge/Redis-Optional-red.svg)](https://redis.io/)

</div>

---

> **与根目录 README 的关系**  
> 项目简介、核心特性、**Docker 一键部署**（克隆仓库、`./docker/deploy.sh`、访问 **`http://localhost:8030`**、默认账号 **`admin` / `admin123`**）、**部署脚本自动完成项**、**常用 Docker 命令**（`cd docker` 后 `compose up/down/restart`、`docker logs`、`docker exec`、更新重建等），以及 **`docker/.env` 中与根 README 一致的环境变量表**（`HOST_PORT`、`GPU_COUNT`、`DATABASE_TYPE`、`MEM_LIMIT` 等），均以 **[仓库根 README](../README.md)** 为准，本文不再重复展开。  
> **本文档** 仅补充：Docker 宿主机软件与资源、GPU 容器工具链、**手动编排步骤**、**`docker/.env` 全量说明与示例**、**Windows 卷挂载**、**数据目录结构**、**compose 运维命令**、**Docker 专项 FAQ** 与 **性能 / 安全建议**。

---

## 📋 本文目录

- [快速入口（摘要）](#-快速入口摘要)
- [环境要求](#-环境要求)
- [一键部署脚本](#一键部署脚本)
- [Windows 部署注意事项](#-windows-部署注意事项)
- [手动部署](#-手动部署)
- [配置说明](#-配置说明)
- [数据目录结构](#-数据目录结构)
- [常用命令](#-常用命令)
- [常见问题](#-常见问题)
- [性能优化](#-性能优化)
- [安全建议](#-安全建议)
- [获取帮助](#-获取帮助)

---

## 🎯 快速入口（摘要）

若尚未阅读仓库主文档，请先打开 **[../README.md](../README.md)** 中的 **「🐳 Docker 一键部署」**。

```bash
git clone https://github.com/syd168/DocuLogic.git
cd DocuLogic
./docker/deploy.sh
```

访问地址与端口说明、默认管理员账号、脚本自动完成事项及 `docker compose` 日常命令，均以根 README 为准；进入 `docker` 目录后常用：

```bash
cd docker
docker compose up -d --build
docker logs -f doculogic
```

---

## 💻 环境要求

**整机硬件建议**（与根 README「前置要求 / 注意事项」一致）：建议 **16GB+ 内存**、**GPU 16GB+ 显存**（可选）、磁盘预留模型与输出空间。下表为 **Docker 宿主机** 安装层面的最低要求。

### 必需软件

| 软件 | 版本要求 | 安装指南 |
|------|---------|----------|
| Docker | 20.10+ | [官方文档](https://docs.docker.com/get-docker/) |
| Docker Compose | v2.0+ | [安装指南](https://docs.docker.com/compose/install/) |
| Git | 任意 | `sudo apt install git` |

### 推荐配置（宿主机）

| 资源 | 最低要求 | 推荐配置 |
|------|---------|----------|
| CPU | 4 核心 | 8+ 核心 |
| 内存 | 8 GB（仅容器编排下限） | **16–32 GB**（与根 README 生产建议一致） |
| 磁盘 | 50 GB | 100+ GB (SSD) |
| GPU | 可选 | NVIDIA 16GB+ 显存 |

### GPU 支持（可选）

如需启用 GPU 加速，需要安装：

```bash
# 1. 安装 NVIDIA 驱动
sudo apt install nvidia-driver-535  # Ubuntu

# 2. 安装 NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 3. 验证 GPU 支持
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

---

## 🚀 一键部署脚本

```
# 1. 克隆项目
git clone https://github.com/syd168/DocuLogic.git
cd DocuLogic

# 2. 执行一键部署
./docker/deploy.sh
```

### ✨ 智能特性

**🔄 自动数据迁移**：
- 当从 SQLite 切换到 MySQL/MariaDB/PostgreSQL 时，部署脚本会**自动检测并迁移数据**
- 原始 SQLite 数据会被保留，确保可随时回滚
- 无需手动运行迁移脚本，实现无缝切换

**📋 SQLite 数据库自动同步**：
- 部署时自动检测项目根目录的 `web/data/app.db`
- 如果存在，自动复制到 Docker 卷挂载点 `${DATA_DIR}/database/sqlite/app.db`
- 智能判断：仅在源文件更新或目标不存在时复制
- **强制覆盖**：使用 `-f` 或 `--force-copy` 参数强制覆盖现有数据库

**🔒 安全保障**：
- 自动生成随机 JWT_SECRET（生产环境必需）
- 检查 Docker 权限和依赖目录
- 清理残留容器，避免端口冲突

**📊 多数据库支持**：
通过修改 `.env` 中的 `DATABASE_TYPE` 即可切换：
```bash
DATABASE_TYPE=sqlite      # 默认，无需额外服务（文件数据库）
DATABASE_TYPE=mysql       # MySQL 8.0（独立容器）
DATABASE_TYPE=mariadb     # MariaDB 10.11（独立容器）
DATABASE_TYPE=postgresql  # PostgreSQL 16（独立容器）
```

**💡 智能容器管理**：
- ✅ **按需创建容器**：只启动你选择的数据库类型对应的容器
- ✅ **自动清理残留**：切换数据库类型时，自动删除不需要的旧容器
- ✅ **SQLite 特殊优化**：作为文件数据库，直接通过卷挂载使用，无需独立服务
- ✅ **数据无缝迁移**：从 SQLite 切换到其他数据库时，自动执行数据转换

### 🛠️ 命令行参数

```bash
# 基本部署
./docker/deploy.sh

# 强制覆盖 SQLite 数据库（即使目标已存在）
./docker/deploy.sh --force-copy
# 或简写
./docker/deploy.sh -f

# 跳过自动数据迁移
./docker/deploy.sh --skip-migration

# 查看帮助
./docker/deploy.sh --help
```

---

## 🪟 Windows 部署注意事项

### Docker Desktop for Windows 配置

1. **安装 Docker Desktop**
   - 下载并安装 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
   - 确保启用 WSL 2 后端（推荐）

2. **配置文件共享**
   - 打开 Docker Desktop → Settings → Resources → File Sharing
   - 添加你计划用于数据存储的驱动器（例如 `C:`、`D:` 等）
   - 点击 "Apply & Restart"

3. **设置环境变量**

   在 PowerShell 中：
   ```powershell
   # 设置数据目录（使用绝对路径）
   $env:DATA_DIR="C:/Users/YourName/doculogic/data"
   $env:MODEL_DIR="C:/Users/YourName/doculogic/weights"
   
   # 启动服务
   docker compose up -d --build
   ```

   或者创建 `.env` 文件：
   ```bash
   # .env 文件内容
   DATA_DIR=C:/Users/YourName/doculogic/data
   MODEL_DIR=C:/Users/YourName/doculogic/weights
   JWT_SECRET=your-secure-jwt-secret
   ```

4. **路径格式要求**
   - ✅ 正确：`C:/Users/Name/doculogic/data` （使用正斜杠）
   - ✅ 正确：`C:\\Users\\Name\\doculogic\\data` （双反斜杠转义）
   - ❌ 错误：`~/doculogic/data` （Linux 风格，Windows 不支持）
   - ❌ 错误：`C:\Users\Name\doculogic\data` （单反斜杠会被转义）

5. **GPU 支持**
   - 需要安装 NVIDIA 驱动和 CUDA Toolkit
   - Docker Desktop 会自动检测 GPU
   - 验证：`docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi`

### 常见问题

**问题 1：卷挂载失败**
```
Error response from daemon: invalid mode: /data/output
```
**解决**：检查路径格式，确保使用正斜杠或双反斜杠

**问题 2：权限被拒绝**
```
Permission denied: '/app/weights'
```
**解决**：在 Docker Desktop 中确认已添加对应驱动器的文件共享权限

**问题 3：模型加载缓慢**
**解决**：将模型放在 SSD 上，避免使用网络驱动器

---

## 🔧 手动部署

以下适用于**不通过** `./docker/deploy.sh`、需自行准备目录与模型的场景。若使用一键部署，目录与密钥多由脚本创建，详见根 README **「Docker 一键部署」**。

### 📌 重要说明：容器启动流程

DocuLogic Docker 容器使用 **`entrypoint.sh`** 作为入口脚本，负责：

1. **加载环境变量**：如果存在 `/app/.env` 文件，会自动加载（作为 docker-compose environment 的补充）
2. **检查目录结构**：自动创建必要的目录（logs, output, data, backups）
3. **启动服务**：按顺序启动 Nginx → Cron → FastAPI 后端

**这意味着：**
- ✅ 你可以将 `.env` 文件复制到容器中，它会被自动加载
- ✅ 所有配置优先使用 docker-compose.yml 中定义的环境变量
- ✅ `.env` 文件仅作为备用配置源

### 步骤 1：准备数据目录

```bash
# 创建数据存储目录（与 compose 中 DATA_DIR / MODEL_DIR 默认值对应时可按需调整）
mkdir -p ~/doculogic/{weights,output,database,logs,uploads}

# 设置权限
chmod -R 755 ~/doculogic
```

### 步骤 2：下载模型权重

容器支持无模型启动。推荐先完成部署，再在后台 **「模型配置」** 中下载模型到 **`MODEL_DIR` 映射目录**（默认见 `docker-compose.yml`，一般为 `~/doculogic/weights/logics-parsing-v2/`）。

```bash
cd /path/to/DocuLogic
# 推荐：启动容器后在后台「模型配置」中下载（路径统一为 weights/文档解析器名称）
# 或手动从 HuggingFace 下载后解压到 MODEL_DIR 对应宿主机目录：
# https://huggingface.co/Logics-MLLM/Logics-Parsing-v2
```

### 步骤 3：配置环境变量

在 **`docker/`** 目录维护 **`docker/.env`**（与 `./docker/deploy.sh` 一致）。根目录 **`.env.example`** 用于**本机直接跑后端**，路径语义不同，请勿混用。

```bash
cd docker
nano .env
```

**关键配置项（须与当前 `docker-compose.yml` 挂载一致）：**

```bash
# ========== 必需配置 ==========
# JWT 密钥（生产环境务必修改！）
JWT_SECRET=$(openssl rand -hex 32)

# 模型路径（容器内路径，与 compose 默认一致；须指向含 config.json 的文档解析器目录）
MODEL_PATH=/app/weights/logics-parsing-v2

# 输出目录（容器内路径，与 compose 默认一致）
OUTPUT_DIR=/data/output

# 管理员用户名
ADMIN_USERNAMES=admin

# ========== Redis 配置（推荐）==========
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# ========== 邮件配置（可选）==========
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USER=your_email@qq.com
SMTP_PASSWORD=your_smtp_password
EMAIL_MOCK=true  # 开发环境设为 true

# ========== 其他配置 ==========
LOG_LEVEL=INFO
# 须包含浏览器地址栏的完整来源（含端口），多个用英文逗号分隔
CORS_ORIGINS=http://localhost:8030,http://127.0.0.1:8030,http://localhost,http://127.0.0.1,http://localhost:5173,http://127.0.0.1:5173
```

### 步骤 4：启动服务

```bash
# 进入 docker 目录
cd docker

# 启动所有服务（包括 Redis）
docker compose up -d --build
```

### 步骤 5：验证部署

```bash
# 查看容器状态
docker ps | grep doculogic

# 查看日志
docker logs -f doculogic

# 健康检查
curl http://localhost:8030/health

# 访问应用
# 浏览器打开: http://localhost:8030
```

---

## ⚙️ 配置说明

### Docker Compose 环境变量

| 变量 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `HOST_PORT` | 访问端口 | `8030` | `8080` |
| `DATA_DIR` | 数据目录 | `~/doculogic/data` | `/mnt/data/doculogic` |
| `MODEL_DIR` | 模型目录 | `~/doculogic/weights` | `/ssd/weights` |
| `GPU_COUNT` | GPU数量（0=禁用） | `0` | `1` |
| `JWT_SECRET` | JWT密钥 | `change-me` | `$(openssl rand -hex 32)` |
| `MEM_LIMIT` | 内存限制 | `8g` | `16g` |
| `CPU_LIMIT` | CPU限制 | `4.0` | `8.0` |
| `REDIS_ENABLED` | 启用Redis | `true` | `false` |

### 使用示例

```bash
# 自定义端口
HOST_PORT=8080 docker compose up -d

# 启用GPU
echo "GPU_COUNT=1" >> .env
docker compose up -d

# 自定义数据路径
DATA_DIR=/my/data MODEL_DIR=/my/weights docker compose up -d

# 限制资源
echo "MEM_LIMIT=16g" >> .env
echo "CPU_LIMIT=8.0" >> .env
docker compose up -d
```

---

## 📁 数据目录结构

```
~/doculogic/
├── weights/                  # 模型权重（按文档解析器分子目录，如 logics-parsing-v2/）
│   └── Logics-Parsing-v2/   # 模型文件
├── data/
│   ├── output/              # 解析输出结果
│   │   ├── {job_id}/        # 每个任务的输出
│   │   │   ├── assets/      # 图片文件
│   │   │   ├── pages/       # 分页结果
│   │   │   └── *.mmd        # Markdown 文件
│   ├── logs/                # 应用日志
│   │   └── app.log
│   ├── database/            # SQLite 数据库
│   │   └── app.db
│   └── uploads/             # 临时上传文件
└── redis/                   # Redis 数据（如启用）
    └── dump.rdb
```

**重要提示：**
- ✅ 所有数据持久化在 `~/doculogic/` 目录
- ✅ 容器删除后数据不会丢失
- ✅ 定期清理 `output/` 和 `uploads/` 释放空间
- ✅ 备份 `database/app.db` 以保留用户数据

---

## 🔍 常用命令

### 服务管理

```bash
# 启动服务
docker compose up -d

# 停止服务
docker compose down

# 重启服务
docker compose restart

# 查看服务状态
docker compose ps
```

### 📝 日志查看（重要）

Docker 环境有两套日志系统，根据问题类型选择：

#### 1️⃣ **应用业务日志**（推荐用于排查 API 错误、数据库问题）

```bash
# 实时查看应用日志（结构化，包含时间戳、级别、模块）
docker exec doculogic tail -f /app/logs/app.log

# 查看最近 100 行
docker exec doculogic tail -n 100 /app/logs/app.log

# 搜索错误
docker exec doculogic grep "ERROR" /app/logs/app.log

# 导出日志到本地
docker cp doculogic:/app/logs/app.log ./app.log
```

**日志格式示例：**
```
2026-05-01 17:17:33,821 | INFO | app.cache | ✅ Redis 连接成功: localhost:6379/0
2026-05-01 17:17:33,821 | ERROR | app.routers.upload | ❌ 文件上传失败: ...
```

#### 2️⃣ **容器运行日志**（推荐用于排查启动失败、进程崩溃）

```bash
# 实时查看容器 stdout/stderr
docker logs -f doculogic

# 查看最近 50 行
docker logs --tail 50 doculogic

# 查看特定时间段
docker logs --since 10m doculogic  # 最近 10 分钟
```

**日志内容：**
- Nginx 启动信息
- Cron 定时任务执行记录
- FastAPI 启动过程
- print() 语句输出

#### 3️⃣ **其他服务日志**

```bash
# Redis 日志
docker logs doculogic-redis

# MySQL/MariaDB/PostgreSQL 日志（根据配置）
docker logs doculogic-mysql
docker logs doculogic-mariadb
docker logs doculogic-postgresql
```

### 🛠️ 调试与维护

```bash
# 进入容器 shell
docker exec -it doculogic bash

# 检查容器健康状态
docker inspect --format='{{.State.Health.Status}}' doculogic

# 查看容器资源使用
docker stats doculogic

# 查看环境变量
docker exec doculogic env | grep -E "(JWT|DATABASE|MODEL)"

# 测试后端健康检查
docker exec doculogic curl -s http://localhost:8000/health

# 测试 Nginx 代理
docker exec doculogic curl -s http://localhost/health
```

### 💾 数据备份

```bash
# 手动备份 SQLite 数据库
docker cp doculogic:/app/web/data/app.db ./backup_$(date +%Y%m%d).db

# 使用内置备份脚本（每天凌晨 2 点自动执行）
docker exec doculogic bash /app/backup_database.sh

# 备份整个数据目录
tar czf doculogic_backup_$(date +%Y%m%d).tar.gz ~/doculogic/
```

### 🔄 更新与重建

```bash
# 拉取最新代码
git pull origin main

# 重新构建并启动
cd docker
docker compose down
docker compose build --no-cache
docker compose up -d

# 仅重建应用容器（保留数据库）
docker compose up -d --build doculogic
```

---

## ❓ 常见问题

与根 README **「注意事项 → 常见问题」** 中通用说明互补；本节侧重 **容器与卷路径**。

**路径约定（与 `docker-compose.yml` 一致）：** 宿主机 `MODEL_DIR`（默认 `~/doculogic/weights`）挂载为容器 **`/app/weights`**；`MODEL_PATH` 默认为 **`/app/weights/logics-parsing-v2`**（须为含 `config.json` 的 HuggingFace 式快照目录）。若系统设置里曾填写 `/app/weights/...`，请确保为 `/app/weights/...` 后保存并重启容器。

### Q1: 容器启动失败，提示 "model not found"

**A:** 确保模型权重已放在 **`MODEL_DIR` 映射目录**（默认 `~/doculogic/weights/logics-parsing-v2/`，见 `docker-compose.yml`）：

```bash
# 检查模型目录
ls -lh ~/doculogic/weights/logics-parsing-v2/

# 若为空：启动容器后在后台「模型配置」重新下载
cd docker && docker compose restart
```

### Q2: GPU 无法识别

**A:** 检查 NVIDIA Container Toolkit 是否正确安装：

```bash
# 验证 GPU 支持
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# 如果失败，重新配置
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 检查 .env 配置
echo "GPU_COUNT=1" >> .env
docker compose up -d
```

### Q3: 内存不足导致容器被杀死

**A:** 调整内存限制或增加系统 swap：

```bash
# 方法一：增加内存限制
echo "MEM_LIMIT=16g" >> .env
docker compose up -d

# 方法二：添加 swap（Ubuntu）
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Q4: Redis 连接失败

**A:** 检查 Redis 容器状态：

```bash
# 查看 Redis 日志
docker logs redis

# 重启 Redis
docker compose restart redis

# 如果不需要 Redis，禁用它
echo "REDIS_ENABLED=false" >> .env
docker compose up -d
```

### Q5: 端口冲突

**A:** 修改 HOST_PORT：

```bash
# 查看占用端口的进程
sudo lsof -i :8030

# 修改端口
echo "HOST_PORT=8080" >> .env
docker compose up -d
```

### Q6: 如何备份数据？

**A:** 定期备份数据库和输出文件：

```bash
# 创建备份脚本
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=~/doculogic/backups/$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# 备份数据库
docker cp doculogic:/app/data/database/app.db $BACKUP_DIR/

# 备份配置文件
cp ~/doculogic/.env $BACKUP_DIR/ 2>/dev/null || true

# 压缩备份
tar czf $BACKUP_DIR.tar.gz -C ~/doculogic backups/$(date +%Y%m%d_%H%M%S)
rm -rf $BACKUP_DIR

echo "备份完成: $BACKUP_DIR.tar.gz"
EOF

chmod +x backup.sh
./backup.sh
```

### Q7: 如何重置管理员密码？

**A:** 进入容器执行 SQL：

```bash
docker exec -it doculogic python << 'EOF'
from app.database import SessionLocal
from app.models import User
from app.auth_security import hash_password

db = SessionLocal()
user = db.query(User).filter(User.username == "admin").first()
if user:
    user.hashed_password = hash_password("new_password_123")
    db.commit()
    print("密码已重置为: new_password_123")
else:
    print("用户不存在")
db.close()
EOF
```

### Q8: 磁盘空间不足

**A:** 清理旧任务和 Docker 缓存：

```bash
# 清理 7 天前的任务
docker exec doculogic find /app/data/output -type d -mtime +7 -exec rm -rf {} +

# 清理 Docker 缓存
docker system prune -a --volumes

# 查看磁盘使用
du -sh ~/doculogic/*
```

---

## 🚀 性能优化

### 1. 启用 GPU 加速

```bash
echo "GPU_COUNT=1" >> .env
docker compose up -d
```

**预期提升：**
- PDF 解析速度：**5-10x**
- 图片处理速度：**3-5x**

### 2. 启用 Redis 缓存

```bash
# 默认已启用，确认配置
grep REDIS_ENABLED .env
# 应该显示: REDIS_ENABLED=true
```

**预期提升：**
- 验证码读写：**10x**
- 速率限制：**分布式支持**
- 会话管理：**更高效**

### 3. 调整资源限制

```bash
# 根据服务器配置调整
echo "MEM_LIMIT=16g" >> .env
echo "CPU_LIMIT=8.0" >> .env
docker compose up -d
```

### 4. 使用 SSD 存储

```bash
# 将数据目录移动到 SSD
mkdir -p /ssd/doculogic
cp -r ~/doculogic/* /ssd/doculogic/

# 修改 .env
echo "DATA_DIR=/ssd/doculogic/data" >> .env
echo "MODEL_DIR=/ssd/doculogic/weights" >> .env

docker compose up -d
```

**预期提升：**
- 模型加载速度：**2-3x**
- 文件读写速度：**5-10x**

---

## 🔐 安全建议

### 生产环境必做

1. **修改 JWT 密钥**
   ```bash
   echo "JWT_SECRET=$(openssl rand -hex 32)" >> .env
   ```

2. **启用 HTTPS**
   - 使用 Nginx 反向代理
   - 配置 Let's Encrypt 证书

3. **配置防火墙**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

4. **禁用模拟邮件**
   ```bash
   echo "EMAIL_MOCK=false" >> .env
   # 配置真实 SMTP
   ```

5. **定期更新**
   ```bash
   # 每周检查更新（与根 README 一致）
   git pull origin main && ./docker/deploy.sh
   ```

---

## 📞 获取帮助

- 📖 **主文档（以仓库根 README 为准）**：[../README.md](../README.md)
- 🐛 报告问题：[GitHub Issues](https://github.com/syd168/DocuLogic/issues)
- 💬 讨论区：[GitHub Discussions](https://github.com/syd168/DocuLogic/discussions)

---

<div align="center">

**部署遇到问题？欢迎提 Issue！**

Made with ❤️ by the DocuLogic Team

</div>
