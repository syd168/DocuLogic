# DocuLogic Docker 部署指南

<div align="center">

**🚀 5分钟快速部署智能文档解析平台**

[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![GPU](https://img.shields.io/badge/GPU-Supported-green.svg)](https://developer.nvidia.com/cuda-zone)
[![Redis](https://img.shields.io/badge/Redis-Optional-red.svg)](https://redis.io/)

</div>

---

## 📋 目录

- [快速开始](#-快速开始)
- [环境要求](#-环境要求)
- [一键部署](#-一键部署)
- [手动部署](#-手动部署)
- [配置说明](#-配置说明)
- [常见问题](#-常见问题)
- [性能优化](#-性能优化)

---

## 🎯 快速开始

### 方式一：一键部署脚本（⭐ 推荐）

```bash
# 1. 克隆项目
git clone https://github.com/your-username/DocuLogic.git
cd DocuLogic

# 2. 执行一键部署
./docker/deploy.sh

# 3. 访问应用
# 浏览器打开: http://localhost
# 默认账号: admin / admin123
```

**脚本会自动完成：**
- ✅ 检查 Docker 和 Docker Compose
- ✅ 检测 NVIDIA GPU（如可用）
- ✅ 创建数据目录结构
- ✅ 下载模型权重（首次运行）
- ✅ 生成安全的 JWT 密钥
- ✅ 配置 Redis 缓存
- ✅ 构建并启动所有服务
- ✅ 验证部署状态

### 方式二：Docker Compose 命令

```bash
# 进入 docker 目录
cd docker

# 启动所有服务
docker compose up -d --build

# 查看日志
docker logs -f doculogic
```

---

## 💻 环境要求

### 必需软件

| 软件 | 版本要求 | 安装指南 |
|------|---------|----------|
| Docker | 20.10+ | [官方文档](https://docs.docker.com/get-docker/) |
| Docker Compose | v2.0+ | [安装指南](https://docs.docker.com/compose/install/) |
| Git | 任意 | `sudo apt install git` |

### 推荐配置

| 资源 | 最低要求 | 推荐配置 |
|------|---------|----------|
| CPU | 4 核心 | 8+ 核心 |
| 内存 | 8 GB | 16-32 GB |
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

## 🚀 一键部署

### 使用 deploy.sh 脚本

```bash
# 赋予执行权限
chmod +x docker/deploy.sh

# 运行部署脚本
./docker/deploy.sh
```

**脚本功能：**
1. 环境检查（Docker、GPU）
2. 创建目录结构
3. 下载模型（如需要）
4. 生成配置文件
5. 启动服务
6. 健康检查

---

## 🔧 手动部署

### 步骤 1：准备数据目录

```bash
# 创建数据存储目录
mkdir -p ~/doculogic/{weights,output,database,logs,uploads}

# 设置权限
chmod -R 755 ~/doculogic
```

### 步骤 2：下载模型权重

```bash
# 方法一：使用下载脚本
cd /path/to/DocuLogic
python logics-parsingv2/download_model_v2.py

# 移动模型到数据目录
mv logics-parsingv2/weights/Logics-Parsing-v2 ~/doculogic/weights/

# 方法二：手动下载
# 访问 https://huggingface.co/Logics-MLLM/Logics-Parsing-v2
# 下载后解压到 ~/doculogic/weights/Logics-Parsing-v2
```

### 步骤 3：配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置
nano .env
```

**关键配置项：**

```bash
# ========== 必需配置 ==========
# JWT 密钥（生产环境务必修改！）
JWT_SECRET=$(openssl rand -hex 32)

# 模型路径（容器内路径）
MODEL_PATH=/app/models/Logics-Parsing-v2

# 输出目录
OUTPUT_DIR=/app/data/output

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
CORS_ORIGINS=http://localhost,http://localhost:8030
```

### 步骤 4：启动服务

```bash
# 进入 docker 目录
cd docker

# 启动所有服务（包括 Redis）
docker compose up -d --build

# 仅启动主服务（不使用 Redis）
docker compose -f docker-compose.simple.yml up -d --build
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
| `MODEL_DIR` | 模型目录 | `~/doculogic/models` | `/ssd/models` |
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
DATA_DIR=/my/data MODEL_DIR=/my/models docker compose up -d

# 限制资源
echo "MEM_LIMIT=16g" >> .env
echo "CPU_LIMIT=8.0" >> .env
docker compose up -d
```

---

## 📁 数据目录结构

```
~/doculogic/
├── weights/                  # 模型权重
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

# 重新构建并启动
docker compose up -d --build

# 查看运行状态
docker compose ps
```

### 日志查看

```bash
# 查看所有日志
docker compose logs -f

# 仅查看主应用日志
docker logs -f doculogic

# 查看最近 100 行
docker logs --tail 100 doculogic

# 导出日志到文件
docker logs doculogic > doculogic.log 2>&1
```

### 进入容器

```bash
# 进入主应用容器
docker exec -it doculogic bash

# 进入 Redis 容器
docker exec -it redis redis-cli

# 查看容器资源占用
docker stats doculogic
```

### 数据管理

```bash
# 备份数据库
docker cp doculogic:/app/data/database/app.db ./backup_$(date +%Y%m%d).db

# 清理旧任务（保留最近7天）
docker exec doculogic python -c "
from app.database import SessionLocal
from app.models import ParseJob
from datetime import datetime, timedelta
db = SessionLocal()
cutoff = datetime.utcnow() - timedelta(days=7)
db.query(ParseJob).filter(ParseJob.created_at < cutoff).delete()
db.commit()
print('清理完成')
"

# 清理 Docker 缓存
docker system prune -a
```

### 更新版本

```bash
# 拉取最新代码
git pull

# 重新构建并启动
./docker/deploy.sh

# 或手动更新
docker compose down
docker compose up -d --build
```

---

## ❓ 常见问题

### Q1: 容器启动失败，提示 "model not found"

**A:** 确保模型权重已正确下载并放置在指定目录：

```bash
# 检查模型目录
ls -lh ~/doculogic/weights/Logics-Parsing-v2/

# 如果为空，重新下载
python logics-parsingv2/download_model_v2.py
mv logics-parsingv2/weights/Logics-Parsing-v2 ~/doculogic/weights/

# 重启服务
docker compose restart
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
   # 每周检查更新
   git pull && ./docker/deploy.sh
   ```

---

## 📞 获取帮助

- 📖 主文档：[../README.md](../README.md)
- 🐛 报告问题：[GitHub Issues](https://github.com/your-username/DocuLogic/issues)
- 💬 讨论区：[GitHub Discussions](https://github.com/your-username/DocuLogic/discussions)

---

<div align="center">

**部署遇到问题？欢迎提 Issue！**

Made with ❤️ by the DocuLogic Team

</div>
