# DocuLogic v1.0.0

<div align="center">

**智能文档解析与结构化平台 | Intelligent Document Parsing & Structuring Platform**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen.svg)](https://vuejs.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](LICENSE)

[🚀 快速开始](#-快速开始) • [📸 功能展示](#-功能展示) • [🏗️ 架构设计](#️-架构设计) • [📝 API 文档](#-api-文档)

</div>

## 📖 项目简介

DocuLogic 是基于阿里巴巴 **Logics-Parsing-v2** 模型的企业级文档解析平台，支持 PDF、图片等多格式文档的结构化转换。

### ✨ 核心特性

- **🎯 强大解析能力**：端到端单模型，支持 STEM 内容（公式、化学结构）、复杂版面、Parsing-2.0（流程图、乐谱）
- **👥 完善用户系统**：注册登录、SSO 单点登录、异地登录检测、强制登出
- **⚙️ 灵活配置管理**：动态调整解析参数、文件上传控制、多数据库支持（SQLite/MySQL/PostgreSQL/MariaDB）
- **📊 全面任务管理**：WebSocket 实时进度、历史记录查询、多种输出模式（Base64/独立文件/不输出）
- **🔐 企业级安全**：JWT + Token 黑名单、7 个安全响应头、日志脱敏、速率限制
- **🛠️ 智能运维工具**：自动化数据迁移、跨数据库类型切换、网络别名自动配置

## 🚀 快速开始

### 前置要求

- Python 3.10+ / Node.js 18+（本地开发）
- Docker & Docker Compose（推荐部署）
- 16GB+ RAM，GPU 推荐（CPU 也可运行）
- 部署前请先准备本地 `converts/models/` 目录（至少包含一个转换器源码子目录；该目录不提交到 GitHub）
- `converts/models` 推荐来源：`Logics-Parsing`（[GitHub](https://github.com/alibaba/Logics-Parsing)）与 `PaddleOCR`（[GitHub](https://github.com/PaddlePaddle/PaddleOCR)）

---

### 🐳 Docker 一键部署（⭐ 推荐）

```bash
# 1. 克隆项目
git clone https://github.com/syd168/DocuLogic.git
cd DocuLogic

# 2. 一键部署（会先检查 converts/models 目录是否存在且非空）
./docker/deploy.sh

# 3. 访问应用
# http://localhost:8030
# 默认账号: admin / admin123
```

**部署脚本自动完成：**
- ✅ 检查 Docker、GPU 环境
- ✅ 创建数据目录（~/doculogic/）；模型默认放在 **`~/doculogic/weights/<转换器名>/`**（容器内为 **`/app/weights/<转换器名>/`**，`MODEL_PATH` 指向含 `config.json` 的快照目录，详见 [docker/README.md](docker/README.md)）
- ✅ 校验本地 `converts/models` 目录（不存在或为空会中止部署）
- ✅ 生成安全密钥（JWT_SECRET）
- ✅ 启动服务（主应用 + Redis + SQLite/MySQL/PostgreSQL/MariaDB）
- ✅ 智能检测数据库迁移需求

#### 常用 Docker 命令

```bash
cd docker

# 启动/停止/重启
docker compose up -d
docker compose down
docker compose restart

# 查看日志
docker logs -f doculogic

# 进入容器
docker exec -it doculogic bash

# 更新版本
git pull origin main
docker compose down && docker compose up -d --build
```

#### 环境变量配置

编辑 `docker/.env` 文件：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `HOST_PORT` | 访问端口 | `8030` |
| `GPU_COUNT` | GPU 数量（0=禁用） | `1` |
| `DATABASE_TYPE` | 数据库类型 | `sqlite` |
| `MEM_LIMIT` | 内存限制 | `8g` |

> 📖 **Docker 专项补充**（宿主机 GPU、Windows 挂载、`docker/.env` 全量、数据目录与排障）：[docker/README.md](docker/README.md) — **通用快速开始与本表以本文为准**。

---

### 💻 本地开发部署

```bash
# 1. 克隆项目
git clone https://github.com/syd168/DocuLogic.git
cd DocuLogic

# 2. 安装依赖
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，设置 MODEL_PATH、JWT_SECRET 等

# 4. 启动服务
./start.sh

# 5. 启动后在后台「模型配置」中下载权重（下载路径统一为 weights/转换器名称）
#    注意：本地启动前同样会检查 converts/models 目录是否存在且非空

# 访问
# 前端: http://localhost:5173
# API:  http://localhost:8000/api/docs
```

## 📸 功能展示

### 文档解析
- 拖拽上传或选择文件，支持批量上传

- 实时进度显示，PDF 页数自定义

- 可视化预览（PNG/ZIP），Markdown 下载

  ![文档解析界面](assets/image-20260409192154579.png)

### 后台管理

- 系统设置（注册、验证码、解析限制）

  ![系统设置](assets/image-20260409192539587.png)

- 用户管理（CRUD + 批量操作）

  ![用户管理](assets/image-20260409192456259.png)

- 生成记录查询与清理

  ![生成记录](assets/image-20260409192515300.png)

- 模型下载与重载

  ![模型管理](assets/image-20260409192613196.png)

### 技术栈

**后端**：FastAPI + SQLAlchemy + JWT + Redis  
**前端**：Vue 3 + Element Plus + Vite  
**基础设施**：Docker + Nginx + MySQL/SQLite等  
**AI 引擎**：Logics-Parsing-v2 + PaddleOCR-3.5（插件化调度）

## 📂 项目结构

```
DocuLogic/
├── run_dev.py               # 本地开发：启动/停止 后端 + Vite（等价 ./start.sh）
├── scripts/                 # 运维和管理脚本
│   ├── backup_database.sh   # 数据库备份脚本
│   └── convert_sqlite_to_other.py  # 数据库转换工具
├── docker/                  # Docker 部署
│   ├── deploy.sh            # 一键部署脚本
│   └── docker-compose.yml   # 服务编排
├── frontend/                # Vue 3 前端
│   └── src/views/           # 页面组件
├── web/                     # FastAPI 后端
│   └── app/
│       ├── routers/         # API 路由
│       ├── models.py        # 数据模型
│       └── main.py          # 入口文件
├── converts/models/         # 本地准备的转换器源码目录（不提交到 GitHub，部署前必备）
├── weights/logics-parsing-v2/         # 当前默认转换器模型目录（下载/加载统一路径）
└── README.md
```

## 🔧 配置说明

### 系统设置（管理员）

登录管理后台可调整：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| PDF 最大解析页数 | 单次解析允许的最大页数 | 80 |
| 图片输出模式 | base64/separate/none | base64 |
| 注册开关 | 是否允许新用户注册 | true |
| 验证码开关 | 登录/注册验证码 | false |

### 环境变量

详见 `.env.example`。关键配置：

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `MODEL_PATH` | 模型权重路径（当前默认转换器） | `./weights/logics-parsing-v2` |
| `OUTPUT_DIR` | 解析输出目录 | `./out` |
| `ADMIN_USERNAMES` | 管理员用户名 | `admin` |
| `DATABASE_TYPE` | 数据库类型 | `mysql` / `sqlite` |

## 🚀 版本历史

### v1.0.0 (当前)
- ✨ 重建仓库版本基线：清空历史后，以当前可运行代码作为 1.0 正式起点
- ✨ 保留文档解析主流程：支持 PDF/图片解析、任务管理、后台模型配置与下载
- ✨ 部署约束明确：`converts/models` 不提交到 GitHub，由部署方本地准备
- ✨ 首页体验优化：视觉增强、滚动入场动画、主题跟随系统明暗模式

> 说明：早期版本号记录已归档，当前仓库以 `v1.0.0` 作为新的持续迭代起点。

## ⚠️ 注意事项

### 硬件要求
- **显存**：建议 16GB+ GPU（CPU 也可，速度慢 5-10 倍）
- **内存**：至少 16GB RAM，建议 32GB+
- **磁盘**：模型 10GB + 输出预留 50GB+

### 常见问题

**Q: 部署后无法访问？**  
A: 检查防火墙开放 8030 端口，查看日志 `docker logs doculogic`

**Q: 模型加载失败？**  
A: 确认 `MODEL_PATH` 正确，检查 GPU 驱动

**Q: 如何备份数据？**  

```bash
# MySQL 备份
docker exec doculogic-mysql mysqldump -uroot -p${MYSQL_PASSWORD} doculogic > backup.sql

# 解析结果备份
tar -czf output_backup.tar.gz ~/doculogic/data/output/
```

**Q: 如何更新到最新版本？**  
```bash
git pull origin main
cd docker && docker compose down && docker compose up -d --build
```

## 📝 许可证

本项目采用 Apache 2.0 许可证。详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [Logics-Parsing-v2](https://github.com/alibaba/Logics-Parsing) - 阿里巴巴开源的文档解析模型
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Python Web 框架
- [Vue 3](https://vuejs.org/) - 渐进式 JavaScript 框架

## 📧 联系方式

- 项目主页：[GitHub Repository](https://github.com/syd168/DocuLogic)
- 模型主页：[HuggingFace](https://huggingface.co/Logics-MLLM/Logics-Parsing-v2)
- 在线演示：[ModelScope](https://www.modelscope.cn/studios/Alibaba-DT/Logics-Parsing/summary)

---

**如果这个项目对你有帮助，请考虑给它一个 ⭐ Star！**

Made with ❤️ by the DocuLogic Team

[📄 Apache 2.0 License](LICENSE) • [🐛 报告问题](https://github.com/syd168/DocuLogic/issues) • [💡 提出建议](https://github.com/syd168/DocuLogic/issues)
