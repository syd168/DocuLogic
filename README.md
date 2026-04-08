# DocuLogic v2.0

<div align="center">

**智能文档解析与结构化平台 | Intelligent Document Parsing & Structuring Platform**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen.svg)](https://vuejs.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.0.0-orange.svg)](https://github.com/your-username/DocuLogic/releases/tag/v2.0.0)
[![Security](https://img.shields.io/badge/Security-Audit%20Passed-brightgreen.svg)](doc/安全漏洞分析报告.md)

[📖 简介](#-项目简介) • [🚀 快速开始](#-快速开始) • [📸 功能展示](#-功能展示) • [🏗️ 架构设计](#️-架构设计) • [📝 API 文档](#-api-文档)

</div>

## 📖 项目简介

DocuLogic（Document Logic）是一个企业级智能文档解析平台，基于阿里巴巴开源的 **Logics-Parsing-v2** 模型构建。该平台提供完整的文档解析、用户管理、任务追踪和系统配置功能，能够将复杂版面文档（PDF、图片等）转换为结构化的 Markdown/HTML 输出。

### ✨ 核心特性

#### 🎯 强大的文档解析能力
- **端到端解析**：单模型架构，无需复杂的多阶段流水线
- **多格式支持**：PNG、JPG、WebP、BMP、TIFF、PDF 等主流格式
- **STEM 内容识别**：精准识别科学公式、化学结构（SMILES）、手写文本
- **复杂版面处理**：优秀处理报纸、杂志等多栏复杂布局文档
- **Parsing-2.0**：支持流程图（Mermaid）、乐谱（ABC 记谱法）、伪代码块

#### 👥 完善的用户系统
- **用户认证**：注册、登录、找回密码、邮箱/手机验证码
- **权限管理**：管理员与普通用户分级权限控制
- **会话管理**：单点登录（SSO）、Token 黑名单、强制登出
- **安全机制**：密码强度校验、图形验证码、速率限制、日志脱敏

#### ⚙️ 灵活的系统配置
- **动态配置**：管理员可实时调整 PDF 页数限制、输出模式、超时时间等
- **数据库切换**：支持 SQLite（开发）和 MySQL（生产）无缝切换
- **缓存策略**：Redis 缓存验证码、速率限制、Token 黑名单
- **邮件/SMS**：支持 SMTP 邮件服务和自定义短信接口
- **自动备份**：Docker 内置定时备份，每天凌晨 2 点自动执行

#### 📊 全面的任务管理
- **实时进度**：WebSocket 实时推送解析进度
- **历史记录**：完整的任务查询、结果下载、缓存清理
- **多种输出**：Base64 嵌入、独立文件、不输出图片三种模式
- **批量操作**：支持批量上传、批量清理、批量导出

## 🚀 快速开始

### 前置要求

**最低配置：**
- Python 3.10+
- Docker & Docker Compose（推荐部署方式）
- 至少 16GB RAM（建议 32GB+）
- GPU（推荐，用于模型推理）或 CPU

**本地开发额外需要：**
- Node.js 18+
- Git

---

### 🐳 方式一：Docker 一键部署（⭐ 强烈推荐）

**适合人群**：快速体验、生产环境部署、无需修改代码

#### 5分钟快速启动

```bash
# 1. 克隆项目
git clone https://github.com/your-username/DocuLogic.git
cd DocuLogic

# 2. 一键部署（自动完成所有步骤）
./docker/deploy.sh

# 3. 访问应用
# 浏览器打开: http://localhost:8030
# 默认账号: admin / admin123
```

**部署脚本自动完成：**
- ✅ 检查系统环境（Docker、GPU）
- ✅ 创建数据目录（~/doculogic/）
- ✅ 下载模型权重（如需要）
- ✅ 生成安全密钥（JWT_SECRET、CODE_PEPPER）
- ✅ 构建并启动容器（主应用 + Redis + MySQL）
- ✅ 初始化数据库和系统设置
- ✅ 验证服务健康状态

#### 手动 Docker Compose 部署

如果你不想使用 `deploy.sh` 脚本，也可以直接使用 Docker Compose 命令：

```bash
# 1. 进入 docker 目录
cd docker

# 2. 准备环境变量（首次需要）
cp ../.env.example ../.env
# 编辑 .env 文件，修改 JWT_SECRET 等配置
nano ../.env

# 3. 创建数据目录
mkdir -p ~/doculogic/{data,output,logs,database,models,redis}

# 4. 下载模型（如果还没有）
cd ..
python logics-parsingv2/download_model_v2.py
mv logics-parsingv2/weights/Logics-Parsing-v2 ~/doculogic/models/
cd docker

# 5. 构建并启动服务（包含 Redis）
docker compose up -d --build

# 6. 查看日志
docker compose logs -f
```

#### Docker 部署架构

```
┌──────────────────────────────────────────────┐
│         Docker Compose 服务栈                 │
├──────────────────────────────────────────────┤
│                                              │
│  ┌──────────────┐  ┌──────────┐             │
│  │  doculogic   │──│  Redis   │             │
│  │              │  │          │             │
│  │ • FastAPI    │  │• 缓存    │             │
│  │ • Nginx      │  │• 速率限制│             │
│  │ • GPU支持    │  │• Token黑名单│           │
│  └──────┬───────┘  └──────────┘             │
│         │                                    │
│         ▼                                    │
│  ┌──────────────┐                           │
│  │   MySQL      │                           │
│  │              │                           │
│  │• 用户数据    │                           │
│  │• 任务记录    │                           │
│  │• 系统配置    │                           │
│  └──────────────┘                           │
│                                              │
│  端口: 8030                                  │
└──────────────────────────────────────────────┘
         │
         ▼
  http://localhost:8030
```

**服务组成：**
- **doculogic**: 主应用容器（FastAPI + Nginx + 模型推理）
- **redis**: Redis 缓存容器（验证码、速率限制、Token黑名单）
- **mysql**: MySQL 数据库容器（用户、任务、配置数据）

**数据持久化：**
```
~/doculogic/
├── data/
│   ├── output/      # 解析输出结果
│   ├── logs/        # 应用日志
│   └── mysql/       # MySQL 数据文件
├── redis/           # Redis AOF 持久化数据
└── models/          # 模型权重
```

#### 常用 Docker 命令

```bash
# ========== 基础操作 ==========
cd docker

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

# ========== 日志查看 ==========
# 查看所有日志
docker compose logs -f

# 仅查看主应用
docker logs -f doculogic

# 仅查看 Redis
docker logs -f doculogic-redis

# 仅查看 MySQL
docker logs -f doculogic-mysql

# 查看最近 100 行
docker logs --tail 100 doculogic

# ========== 进入容器 ==========
# 进入主应用
docker exec -it doculogic bash

# 进入 Redis CLI
docker exec -it doculogic-redis redis-cli

# 进入 MySQL CLI
docker exec -it doculogic-mysql mysql -uroot -p

# ========== 资源监控 ==========
# 查看资源占用
docker stats doculogic doculogic-redis doculogic-mysql

# ========== 数据管理 ==========
# 备份 MySQL 数据库
docker exec doculogic-mysql mysqldump -uroot -p${MYSQL_PASSWORD} doculogic > backup_$(date +%Y%m%d).sql

# 恢复 MySQL 数据库
docker exec -i doculogic-mysql mysql -uroot -p${MYSQL_PASSWORD} doculogic < backup_20240101.sql

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

# ========== 更新版本 ==========
git pull origin main
cd docker
docker compose down
docker compose up -d --build
```

#### 环境变量配置

**核心配置项：**

| 变量 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `HOST_PORT` | 访问端口 | `8030` | `8080` |
| `DATA_DIR` | 数据目录 | `~/doculogic/data` | `/mnt/data/doculogic` |
| `MODEL_DIR` | 模型目录 | `~/doculogic/models` | `/ssd/models` |
| `GPU_COUNT` | GPU数量（0=禁用） | `1` | `0` |
| `JWT_SECRET` | JWT密钥 | `自动生成` | `$(openssl rand -hex 32)` |
| `CODE_PEPPER` | 验证码加盐 | `自动生成` | 随机字符串 |
| `MEM_LIMIT` | 内存限制 | `8g` | `16g` |
| `CPU_LIMIT` | CPU限制 | `4.0` | `8.0` |

**数据库配置：**

| 变量 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `DATABASE_TYPE` | 数据库类型 | `mysql` | `sqlite` / `mysql` |
| `MYSQL_HOST` | MySQL主机 | `mysql` | `localhost` |
| `MYSQL_PORT` | MySQL端口 | `3306` | `3306` |
| `MYSQL_USER` | MySQL用户名 | `doculogic` | `root` |
| `MYSQL_PASSWORD` | MySQL密码 | `自动生成` | `your_password` |
| `MYSQL_DATABASE` | 数据库名 | `doculogic` | `doculogic` |

**Redis 配置：**

| 变量 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `REDIS_HOST` | Redis主机 | `redis` | `localhost` |
| `REDIS_PORT` | Redis端口 | `6379` | `6379` |
| `REDIS_DB` | Redis数据库 | `0` | `0-15` |

**使用示例：**

```bash
# 自定义端口
echo "HOST_PORT=8080" >> .env
docker compose up -d

# 启用GPU
echo "GPU_COUNT=1" >> .env
docker compose up -d

# 限制资源
echo "MEM_LIMIT=16g" >> .env
echo "CPU_LIMIT=8.0" >> .env
docker compose up -d

# 切换到 SQLite（开发环境）
echo "DATABASE_TYPE=sqlite" >> .env
docker compose down
docker compose up -d
```

#### GPU 支持

如需启用 GPU 加速，需要先安装 NVIDIA Container Toolkit：

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

# 4. 配置 Docker Compose
echo "GPU_COUNT=1" >> docker/.env
cd docker && docker compose up -d
```

> 📖 **详细文档**：[docker/README.md](docker/README.md) - 包含常见问题解答、性能优化、安全建议等

---

### 💻 方式二：本地开发部署

**适合人群**：开发者、需要调试代码

#### 1. 克隆项目

```bash
git clone https://github.com/your-username/DocuLogic.git
cd DocuLogic
```

#### 2. 下载模型权重

```bash
# 方法一：使用提供的下载脚本
python logics-parsingv2/download_model_v2.py

# 方法二：从 HuggingFace 手动下载
# 访问 https://huggingface.co/Logics-MLLM/Logics-Parsing-v2

# 方法三：从 ModelScope 下载
# 访问 https://www.modelscope.cn/models/Alibaba-DT/Logics-Parsing-v2
```

#### 3. 安装后端依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖（包含 Redis 支持）
pip install -r requirements.txt
```

#### 4. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

#### 5. 配置环境变量

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑 .env 文件
nano .env  # 或使用你喜欢的编辑器
```

关键配置项：
```env
# 模型路径（根据实际位置修改）
MODEL_PATH=./logics-parsingv2/weights/Logics-Parsing-v2

# 输出目录
OUTPUT_DIR=./out

# 管理员用户名
ADMIN_USERNAMES=admin

# JWT 密钥（生产环境务必修改）
JWT_SECRET=$(openssl rand -hex 32)

# Redis 配置（可选，未配置则降级到数据库）
REDIS_HOST=localhost
REDIS_PORT=6379
```

#### 6. 启动 Redis（可选但推荐）

```bash
# 使用 Docker 启动 Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 或使用系统包管理器
# Ubuntu/Debian: sudo apt install redis-server && sudo systemctl start redis
# macOS: brew install redis && brew services start redis
```

#### 7. 启动服务

```bash
# 方法一：使用启动脚本（推荐）
chmod +x start.sh
./start.sh

# 方法二：手动启动
# 终端 1：启动后端
python web_server.py

# 终端 2：启动前端开发服务器
cd frontend
npm run dev
```

#### 8. 访问应用

- 🌐 前端界面：http://localhost:5173
- 📚 API 文档：http://localhost:8000/api/docs
- ❤️ 健康检查：http://localhost:8000/health

## 📸 功能展示

### 文档解析
- 拖拽上传或选择文件
- 支持批量上传
- 实时进度显示
- PDF 页数自定义

### 结果查看
- 可视化预览（PNG/ZIP）
- 原始 Markdown 下载
- 转换后 Markdown 下载
- 完整结果 ZIP（含图片）

### 后台管理
- 系统设置（注册、验证码、PDF 限制等）
- 用户管理（创建、编辑、批量操作）
- 生成记录查询与清理
- 缓存管理
- 模型下载与重载

## 🏗️ 架构设计

### 系统架构图

```
┌───────────────────────────────────────────────────────────────┐
│                        客户端层                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │   Web UI    │  │  Mobile App │  │   API SDK   │           │
│  │  (Vue 3)    │  │  (Future)   │  │  (Future)   │           │
│  └──────┬──────┘  └─────────────┘  └─────────────┘           │
└─────────┼─────────────────────────────────────────────────────┘
          │ HTTP/WebSocket
┌─────────▼─────────────────────────────────────────────────────┐
│                       网关层                                    │
│  ┌───────────────────────────────────────────────────────┐   │
│  │                    Nginx                               │   │
│  │  • 静态文件服务  • 反向代理  • 负载均衡  • SSL终止      │   │
│  └───────────────────────┬───────────────────────────────┘   │
└──────────────────────────┼───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                      应用层                                   │
│  ┌───────────────────────────────────────────────────────┐   │
│  │                  FastAPI Backend                       │   │
│  │                                                       │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐             │   │
│  │  │ Auth     │ │ Parse    │ │ Admin    │             │   │
│  │  │ Router   │ │ Router   │ │ Router   │             │   │
│  │  └──────────┘ └──────────┘ └──────────┘             │   │
│  │                                                       │   │
│  │  ┌──────────────────────────────────────────┐       │   │
│  │  │         Business Logic Layer             │       │   │
│  │  │  • 用户管理  • 会话管理  • 任务调度       │       │   │
│  │  │  • 模型推理  • 邮件/SMS  • 速率限制       │       │   │
│  │  └──────────────────────────────────────────┘       │   │
│  └───────────────────────┬───────────────────────────┘   │
└──────────────────────────┼───────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                      数据层                                   │
│  ┌──────────────┐  ┌──────────┐  ┌──────────────┐         │
│  │   MySQL      │  │  Redis   │  │ File System  │         │
│  │              │  │          │  │              │         │
│  │• 用户数据    │  │• 验证码  │  │• 解析结果    │         │
│  │• 任务记录    │  │• 速率限制│  │• 模型权重    │         │
│  │• 系统配置    │  │• SSO会话 │  │• 上传文件    │         │
│  └──────────────┘  └──────────┘  └──────────────┘         │
└───────────────────────────────────────────────────────────────┘
```

### 技术栈

**后端：**
- **框架**：FastAPI 0.100+（异步、高性能）
- **ORM**：SQLAlchemy 2.0（支持 SQLite/MySQL）
- **认证**：JWT (python-jose) + bcrypt 密码哈希
- **缓存**：Redis 7.x（可选，降级到数据库）
- **WebSocket**：实时进度推送
- **邮件**：SMTP / Mock 模式
- **短信**：HTTP API / Mock 模式

**前端：**
- **框架**：Vue 3 + Composition API
- **UI库**：Element Plus
- **路由**：Vue Router 4
- **状态管理**：Pinia
- **HTTP客户端**：Axios
- **构建工具**：Vite 5

**基础设施：**
- **容器化**：Docker + Docker Compose
- **Web服务器**：Nginx（静态文件 + 反向代理）
- **数据库**：MySQL 8.0 / SQLite 3
- **缓存**：Redis 7
- **GPU加速**：NVIDIA CUDA + PyTorch

**AI 模型：**
- **核心模型**：Logics-Parsing-v2（阿里巴巴开源）
- **深度学习框架**：PyTorch 2.0+
- **Transformer**：HuggingFace Transformers

## 📝 API 文档

启动服务后，访问以下地址查看完整的 API 文档：

- **Swagger UI**: http://localhost:8030/api/docs
- **ReDoc**: http://localhost:8030/api/redoc

### 主要 API 端点

#### 认证相关

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/auth/register` | 用户注册 | ❌ |
| POST | `/api/auth/login` | 用户登录 | ❌ |
| POST | `/api/auth/logout` | 用户登出 | ✅ |
| POST | `/api/auth/forgot-password` | 找回密码 | ❌ |
| POST | `/api/auth/reset-password` | 重置密码 | ❌ |
| GET | `/api/auth/me` | 获取当前用户信息 | ✅ |

#### 文档解析

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/jobs/upload` | 上传并创建解析任务 | ✅ |
| GET | `/api/jobs` | 查询任务列表 | ✅ |
| GET | `/api/jobs/{job_id}` | 查询任务详情 | ✅ |
| DELETE | `/api/jobs/{job_id}` | 删除任务 | ✅ |
| GET | `/api/jobs/{job_id}/result` | 下载解析结果 | ✅ |
| WS | `/ws/jobs/{job_id}` | WebSocket 实时进度 | ✅ |

#### 系统管理（管理员）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/admin/settings` | 获取系统设置 | ✅ Admin |
| PUT | `/api/admin/settings` | 更新系统设置 | ✅ Admin |
| GET | `/api/admin/users` | 查询用户列表 | ✅ Admin |
| POST | `/api/admin/users` | 创建用户 | ✅ Admin |
| PUT | `/api/admin/users/{id}` | 更新用户 | ✅ Admin |
| DELETE | `/api/admin/users/{id}` | 删除用户 | ✅ Admin |
| POST | `/api/admin/users/{id}/kick` | 踢出用户 | ✅ Admin |
| GET | `/api/admin/jobs` | 查询所有任务 | ✅ Admin |
| DELETE | `/api/admin/jobs/cleanup` | 清理旧任务 | ✅ Admin |

### API 使用示例

```bash
# 1. 登录获取 Token
curl -X POST http://localhost:8030/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 响应:
# {"access_token": "eyJhbGci...", "token_type": "bearer"}

# 2. 上传文档进行解析
curl -X POST http://localhost:8030/api/jobs/upload \
  -H "Authorization: Bearer eyJhbGci..." \
  -F "file=@document.pdf" \
  -F "max_pages=50"

# 响应:
# {"job_id": "abc123", "status": "processing", "total_pages": 10}

# 3. 查询任务状态
curl http://localhost:8030/api/jobs/abc123 \
  -H "Authorization: Bearer eyJhbGci..."

# 响应:
# {"job_id": "abc123", "status": "completed", "progress": 100}

# 4. 下载解析结果
curl http://localhost:8030/api/jobs/abc123/result \
  -H "Authorization: Bearer eyJhbGci..." \
  -o result.zip
```

## 📂 项目结构

```
DocuLogic/
├── docker/                     # Docker 部署文件 ⭐
│   ├── Dockerfile              # 多阶段构建镜像
│   ├── docker-compose.yml      # 服务编排配置
│   ├── deploy.sh               # 一键部署脚本
│   ├── nginx/
│   │   └── default.conf        # Nginx 配置
│   └── README.md               # Docker 详细说明
│
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── api/                # API 调用封装
│   │   ├── components/         # 通用组件
│   │   ├── router/             # 路由配置
│   │   ├── styles/             # 全局样式
│   │   ├── views/              # 页面组件
│   │   │   ├── Landing.vue     # 首页
│   │   │   ├── Login.vue       # 登录页
│   │   │   ├── Register.vue    # 注册页
│   │   │   ├── Forgot.vue      # 找回密码
│   │   │   └── Workspace.vue   # 工作台
│   │   ├── App.vue             # 根组件
│   │   └── main.js             # 入口文件
│   ├── package.json            # 前端依赖
│   └── vite.config.js          # Vite 配置
│
├── web/                        # FastAPI 后端
│   ├── app/
│   │   ├── routers/            # API 路由
│   │   │   ├── auth.py         # 认证相关
│   │   │   ├── jobs.py         # 任务管理
│   │   │   └── admin.py        # 管理后台
│   │   ├── auth_security.py    # 密码哈希、JWT
│   │   ├── cache.py            # Redis 缓存封装
│   │   ├── captcha.py          # 图形验证码
│   │   ├── database.py         # 数据库连接与迁移
│   │   ├── deps.py             # 依赖注入
│   │   ├── email_svc.py        # 邮件服务
│   │   ├── job_events.py       # WebSocket 事件
│   │   ├── models.py           # SQLAlchemy 模型
│   │   ├── session_manager.py  # 会话管理 (SSO)
│   │   ├── settings_service.py # 系统设置服务
│   │   ├── sms_svc.py          # 短信服务
│   │   └── model_inference.py  # 模型推理
│   ├── data/                   # SQLite 数据库（开发用）
│   └── static/                 # 静态文件
│
├── logics-parsingv2/           # Logics-Parsing-v2 模型
│   ├── weights/                # 模型权重目录
│   ├── inference_v2.py         # 推理脚本
│   └── download_model_v2.py    # 模型下载脚本
│
├── out/                        # 解析输出目录（自动创建）
├── logs/                       # 应用日志（自动创建）
│
├── .env                        # 环境变量配置（不提交到 Git）
├── .env.example                # 环境变量示例
├── requirements.txt            # Python 依赖
├── start.sh                    # 本地启动脚本
├── stop.sh                     # 本地停止脚本
└── README.md                   # 本文件
```

## 🔧 配置说明

### 系统设置（管理员）

登录管理后台后，可以在“系统设置”页面调整以下配置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| PDF 最大解析页数 | 单次解析允许的最大页数 | 80 |
| 图片输出模式 | base64/separate/none | base64 |
| 显示页码标记 | 是否在结果中包含页码 | true |
| 僵尸任务超时 | 超时判定时间（分钟） | 10 |
| 注册开关 | 是否允许新用户注册 | true |
| 验证码开关 | 登录/注册/找回密码验证码 | false |
| 密码最小长度 | 用户密码最小长度 | 8 |
| 密码复杂度要求 | 大小写、数字、特殊字符 | 可选 |

### 环境变量

详见 `.env.example` 文件。关键配置项：

| 变量名 | 说明 | 示例 |
|--------|------|------|
| MODEL_PATH | 模型权重路径 | `./weights/Logics-Parsing-v2` |
| OUTPUT_DIR | 解析输出目录 | `./out` |
| ADMIN_USERNAMES | 管理员用户名 | `admin,superuser` |
| SMTP_HOST | SMTP 服务器 | `smtp.qq.com` |
| CORS_ORIGINS | 允许的跨域源 | `http://localhost:5173` |
| DATABASE_TYPE | 数据库类型 | `mysql` / `sqlite` |

## 📊 性能指标

Logics-Parsing-v2 模型在多个基准测试中取得 SOTA 成绩：

- **OmniDocBench-v1.5**：总体得分 **93.23**
- **LogicsDocBench**（内部基准）：总体得分 **82.16**
- 支持 9 大类、20+ 小类文档类型
- 优秀的公式、表格、化学结构识别能力

详细 benchmark 数据请参考 [logics-parsingv2/README.md](logics-parsingv2/README.md)

## 🚀 v2.0.0 版本特性

### ✨ 新增功能

#### 1. **企业级安全防护**
- ✅ **安全响应头**：添加 7 个安全响应头（CSP、HSTS、X-Frame-Options 等）
- ✅ **错误信息脱敏**：服务端记录详细日志，用户仅见友好提示
- ✅ **日志脱敏**：邮箱、手机号、用户名自动掩码处理
- ✅ **路径遍历防护**：双重验证防止任意文件读取
- ✅ **SSRF 防护**：SMS HTTP URL 协议校验与内网地址拦截
- ✅ **会话管理增强**：密码重置后自动销毁所有活跃会话
- ✅ **僵尸任务恢复**：乐观锁机制避免竞态条件

#### 2. **自动化运维**
- ✅ **数据库自动备份**：Docker 内置 cron 定时任务，每天凌晨 2 点执行
- ✅ **智能清理**：自动清理过期备份（默认保留 7 天）
- ✅ **多数据库支持**：同时支持 SQLite 和 MySQL 自动备份
- ✅ **备份压缩**：gzip 压缩节省存储空间

#### 3. **UI/UX 优化**
- ✅ **卡片式布局**：系统配置界面重构，信息层次清晰
- ✅ **Tooltip 优化**：结构化展示帮助信息，包含作用、要求、示例
- ✅ **表单简化**：移除冗余按钮，输入框直接显示当前值
- ✅ **视觉统一**：所有 Tooltip 问号样式统一为 `?`
- ✅ **按钮配色优化**：非核心操作使用低调配色
- ✅ **对齐修复**：所有表单项左对齐，视觉流更连贯

#### 4. **部署改进**
- ✅ **单容器部署**：Nginx + FastAPI + cron 整合到一个容器
- ✅ **一键部署脚本**：`deploy.sh` 自动完成所有配置
- ✅ **健康检查增强**：同时检查 Nginx 和后端服务
- ✅ **数据卷挂载**：备份文件自动同步到宿主机

### 🔧 优化改进

#### 性能优化
- 优化 Docker 镜像构建速度（多阶段构建）
- 优化前端加载性能（代码分割、懒加载）
- 优化数据库查询（索引优化、连接池）
- 优化 WebSocket 连接管理（自动重连、心跳检测）

#### 安全性提升
- 安全评分从 7/10 提升至 8.5/10
- 修复 14 个已知安全漏洞
- 通过二次安全审计（发现 8 个新问题，2 High + 3 Medium）
- 建立安全开发生命周期 (SDL) 流程

#### 用户体验
- 简化注册登录流程
- 优化错误提示信息
- 增强移动端适配
- 改善无障碍访问

### 🐛 Bug 修复

- 修复环境变量解析时行尾注释导致的问题
- 修复 Token 解码失败时的错误处理
- 修复系统设置初始化值为 0 的问题
- 修复 Docker 容器中 MySQL 用户权限问题
- 修复 PDF.js Worker 加载失败的问题
- 修复 Nginx 配置变量替换语法错误
- 修复 WebSocket 认证缺少会话验证的问题
- 修复验证码存储降级安全隐患

### 📝 文档完善

- 重写 README.md，增加 v2.0 新特性说明
- 添加详细的 Docker 部署说明
- 添加安全漏洞分析报告（14 个已修复 + 8 个新发现）
- 添加数据库自动备份使用指南
- 添加 API 使用示例
- 添加常见问题解答 (FAQ)

---

## 🚀 v1.0.0 版本特性

### ✨ 新增功能

1. **完整的用户认证系统**
   - 邮箱/手机号注册与登录
   - 图形验证码防暴力破解
   - 找回密码功能
   - 密码强度校验

2. **单点登录 (SSO)**
   - Token 黑名单机制
   - 多终端互斥登录
   - 管理员强制踢出用户
   - 会话管理与追踪

3. **MySQL 数据库支持**
   - 无缝切换 SQLite/MySQL
   - Docker 自动初始化 MySQL
   - 数据库迁移脚本
   - 数据持久化与备份

4. **Redis 缓存集成**
   - 验证码存储
   - 速率限制
   - Token 黑名单
   - 会话管理

5. **完善的部署方案**
   - Docker 一键部署脚本
   - 多阶段构建优化镜像体积
   - Nginx 反向代理
   - GPU 加速支持

6. **管理后台功能**
   - 系统设置动态配置
   - 用户管理（CRUD + 批量操作）
   - 任务查询与清理
   - 模型下载与重载

### 🐛 Bug 修复

- 修复环境变量解析时行尾注释导致的问题
- 修复 Token 解码失败时的错误处理
- 修复系统设置初始化值为 0 的问题
- 修复 Docker 容器中 MySQL 用户权限问题
- 修复 PDF.js Worker 加载失败的问题

### 🔧 优化改进

- 优化数据库迁移逻辑，支持增量更新
- 优化日志输出，区分不同级别的信息
- 优化错误提示，提供更友好的用户反馈
- 优化 Docker 镜像构建速度
- 优化前端加载性能

### 📝 文档完善

- 重写 README.md，增加架构图和 API 文档
- 添加详细的 Docker 部署说明
- 添加常见问题解答 (FAQ)
- 添加 API 使用示例

## 🔐 安全说明

### v2.0 安全改进

本项目已通过**二次安全审计**，安全评分 **8.5/10**。

**已修复漏洞（14个）**：
- ✅ JWT_SECRET 默认值检查
- ✅ WebSocket 会话验证
- ✅ 路径遍历攻击防护
- ✅ 文件上传大小限制
- ✅ CORS 配置收紧
- ✅ 错误信息脱敏
- ✅ 僵尸任务竞态修复
- ✅ 日志脱敏
- ✅ 安全响应头（7个）
- ✅ 数据库备份自动化

**新发现问题（8个）**：
- ⚠️ SMS HTTP URL 协议校验（High）- 待修复
- ⚠️ 密码重置后旧 Token 仍有效（High）- 待修复
- ℹ️ 其他 6 个 Medium/Low/Info 问题 - 计划中

详见：[doc/安全漏洞分析报告.md](doc/安全漏洞分析报告.md)

### 最佳实践

- 默认情况下，邮件和短信服务处于模拟模式
- 生产环境请配置真实的 SMTP 和短信服务
- 建议启用图形验证码防止暴力破解
- 定期更新管理员密码
- 不要将 `.env` 文件提交到版本控制系统
- JWT_SECRET 和 CODE_PEPPER 应使用强随机字符串
- 建议启用 HTTPS（通过 Nginx 配置 SSL 证书）
- 定期检查并应用安全补丁
- 监控异常登录行为

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 许可证

本项目采用 Apache 2.0 许可证。详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [Logics-Parsing-v2](https://github.com/alibaba/Logics-Parsing) - 阿里巴巴开源的文档解析模型
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Python Web 框架
- [Vue 3](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Element Plus](https://element-plus.org/) - Vue 3 组件库

## 📧 联系方式

- 项目主页：[GitHub Repository](https://github.com/your-username/Logics-Parsing-Web)
- 模型主页：[HuggingFace](https://huggingface.co/Logics-MLLM/Logics-Parsing-v2)
- 在线演示：[ModelScope](https://www.modelscope.cn/studios/Alibaba-DT/Logics-Parsing/summary)

## ⚠️ 注意事项

### 硬件要求

1. **显存需求**：模型推理需要较大显存，建议至少 16GB GPU 显存
   - CPU 模式也可以运行，但速度较慢（约慢 5-10 倍）
   - 建议使用 NVIDIA GPU + CUDA 12.0+

2. **内存需求**：至少 16GB RAM，建议 32GB+
   - 大页数 PDF 会消耗较多内存
   - 并发处理多个任务时需要更多内存

3. **磁盘空间**：
   - 模型权重：约 10GB
   - 解析输出：根据文档大小而定，建议预留 50GB+
   - Docker 镜像：约 8GB

### 性能优化

1. **首次加载**：首次加载模型可能需要几分钟，请耐心等待
   - 后续请求会快很多
   - 可以通过日志查看模型加载进度

2. **PDF 处理**：
   - 大页数 PDF 会消耗较多时间和内存
   - 建议设置合理的页数上限（默认 80 页）
   - 可以分批处理大型文档

3. **磁盘清理**：
   - 定期清理 `out/` 目录中的旧文件
   - 使用管理后台的“清理旧任务”功能
   - 建议保留最近 7 天的数据

### 常见问题

**Q: 部署后无法访问？**
A: 检查防火墙是否开放 8030 端口，查看容器日志 `docker logs doculogic`

**Q: 模型加载失败？**
A: 确认模型路径正确，检查 `MODEL_PATH` 环境变量，查看日志确认是否有 GPU 错误

**Q: MySQL 连接失败？**
A: 检查 `.env` 中的数据库配置，确认 MySQL 容器已启动 `docker ps | grep mysql`

**Q: Redis 连接失败？**
A: 应用会自动降级到数据库存储，不影响核心功能。如需修复，检查 Redis 容器状态

**Q: 如何备份数据？**
A: 
```bash
# 备份 MySQL
docker exec doculogic-mysql mysqldump -uroot -p${MYSQL_PASSWORD} doculogic > backup.sql

# 备份 Redis
docker exec doculogic-redis redis-cli BGSAVE

# 备份解析结果
tar -czf output_backup.tar.gz ~/doculogic/data/output/
```

**Q: 如何更新到最新版本？**
A:
```bash
git pull origin main
cd docker
docker compose down
docker compose up -d --build
```

---


**如果这个项目对你有帮助，请考虑给它一个 ⭐ Star！**

Made with ❤️ by the DocuLogic Team

[📄 Apache 2.0 License](LICENSE) • [🐛 报告问题](https://github.com/your-username/DocuLogic/issues) • [💡 提出建议](https://github.com/your-username/DocuLogic/issues)
