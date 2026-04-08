# Logics-Parsing Web Platform

<div align="center">

**基于 Logics-Parsing-v2 的智能文档解析 Web 平台**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](LICENSE)

</div>

## 📖 项目简介

Logics-Parsing Web Platform 是一个功能完整的智能文档解析 Web 应用，基于阿里巴巴开源的 **Logics-Parsing-v2** 模型构建。该平台提供直观的图形界面，支持图片、PDF 等多种格式文档的结构化解析，能够将复杂版面文档转换为结构化的 HTML/Markdown 输出。

### ✨ 核心特性

- **🎯 端到端解析**：单模型架构，无需复杂的多阶段流水线
- **📄 多格式支持**：支持 PNG、JPG、WebP、BMP、TIFF、PDF 等格式
- **🔬 STEM 内容识别**：精准识别科学公式、化学结构（SMILES 格式）、手写文本
- **📊 复杂版面处理**：优秀处理报纸、杂志等多栏复杂布局文档
- **🎵 Parsing-2.0**：支持流程图（Mermaid）、乐谱（ABC 记谱法）、伪代码块
- **👥 多用户系统**：完整的用户注册、登录、权限管理
- **⚙️ 灵活配置**：管理员可配置 PDF 页数限制、输出模式、僵尸任务超时等
- **📈 任务管理**：实时进度追踪、生成记录查询、缓存清理
- **🖼️ 多种输出模式**：Base64 嵌入、独立文件、不输出图片

## 🚀 快速开始

### 前置要求

- Python 3.10+
- Node.js 16+
- GPU（推荐，用于模型推理）或 CPU
- 至少 16GB RAM（建议 32GB+）

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/your-username/Logics-Parsing-Web.git
cd Logics-Parsing-Web
```

#### 2. 下载模型权重

```bash
# 方法一：使用提供的下载脚本
python logics-parsingv2/download_model_v2.py

# 方法二：从 HuggingFace 下载
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

# 安装依赖
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

# 编辑 .env 文件，配置模型路径等
nano .env  # 或使用你喜欢的编辑器
```

关键配置项：
```env
MODEL_PATH=./logics-parsingv2/weights/Logics-Parsing-v2
OUTPUT_DIR=./out
ADMIN_USERNAMES=admin
```

#### 6. 启动服务

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

#### 7. 访问应用

- 前端界面：http://localhost:5173
- API 文档：http://localhost:8000/api/docs
- 健康检查：http://localhost:8000/health

### Docker 部署

#### 方式一：一键部署（⭐ 推荐）

```bash
# 一键部署（自动完成所有步骤）
./docker/deploy.sh

# 访问应用
# http://localhost
```

所有数据存储在 `~/doculogic/` 目录。

#### 方式二：手动部署

```bash
# 准备数据目录
mkdir -p ~/doculogic/{weights,output,database,logs,uploads}

# 下载模型
python logics-parsingv2/download_model_v2.py
# 移动模型到 ~/doculogic/weights/

# 配置环境变量
cp .env.example .env
nano .env  # 修改 JWT_SECRET

# 启动服务
docker compose -f docker/docker-compose.simple.yml up -d --build

# 查看日志
docker compose -f docker/docker-compose.simple.yml logs -f
```

详细文档请参考：
- [docker/README.md](docker/README.md) - Docker 部署详细说明
- [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) - 完整部署指南

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

## 🏗️ 项目结构

```
Logics-Parsing-Web/
├── docker/                 # Docker 部署文件 ⭐
│   ├── Dockerfile.all-in-one      # 单容器全栈镜像
│   ├── nginx-single-container.conf # Nginx 配置
│   ├── docker-compose.simple.yml   # 一键部署配置
│   ├── deploy.sh                  # 一键部署脚本
│   └── README.md                  # Docker 部署说明
├── frontend/               # Vue 3 前端
│   ├── src/
│   │   ├── views/           # 页面组件
│   │   ├── components/      # 通用组件
│   │   ├── api/            # API 调用
│   │   └── router/         # 路由配置
│   └── package.json
├── web/                     # FastAPI 后端
│   ├── app/
│   │   ├── routers/        # API 路由
│   │   ├── models.py       # 数据库模型
│   │   ├── main.py         # 主应用
│   │   └── model_inference.py  # 模型推理
│   └── data/               # SQLite 数据库
├── logics-parsingv2/        # Logics-Parsing-v2 模型
│   ├── weights/            # 模型权重
│   └── inference_v2.py     # 推理脚本
├── out/                     # 解析输出目录
├── docker-compose.yml       # 多容器开发配置
├── requirements.txt         # Python 依赖
└── README.md               # 本文件
```

## 🔧 配置说明

### 系统设置（管理员）

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| PDF 最大解析页数 | 单次解析允许的最大页数 | 80 |
| 图片输出模式 | base64/separate/none | base64 |
| 显示页码标记 | 是否在结果中包含页码 | true |
| 僵尸任务超时 | 超时判定时间（分钟） | 10 |
| 注册开关 | 是否允许新用户注册 | true |
| 验证码开关 | 登录/注册/找回密码验证码 | false |

### 环境变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| MODEL_PATH | 模型权重路径 | `./weights/Logics-Parsing-v2` |
| OUTPUT_DIR | 解析输出目录 | `./out` |
| ADMIN_USERNAMES | 管理员用户名 | `admin,superuser` |
| SMTP_HOST | SMTP 服务器 | `smtp.qq.com` |
| CORS_ORIGINS | 允许的跨域源 | `http://localhost:5173` |

## 📊 性能指标

Logics-Parsing-v2 模型在多个基准测试中取得 SOTA 成绩：

- **OmniDocBench-v1.5**：总体得分 **93.23**
- **LogicsDocBench**（内部基准）：总体得分 **82.16**
- 支持 9 大类、20+ 小类文档类型
- 优秀的公式、表格、化学结构识别能力

详细 benchmark 数据请参考 [logics-parsingv2/README.md](logics-parsingv2/README.md)

## 🔐 安全说明

- 默认情况下，邮件和短信服务处于模拟模式
- 生产环境请配置真实的 SMTP 和短信服务
- 建议启用图形验证码防止暴力破解
- 定期更新管理员密码
- 不要将 `.env` 文件提交到版本控制系统

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

1. **显存需求**：模型推理需要较大显存，建议至少 16GB GPU 显存
2. **首次加载**：首次加载模型可能需要几分钟，请耐心等待
3. **PDF 处理**：大页数 PDF 会消耗较多时间和内存，建议设置合理的页数上限
4. **磁盘空间**：解析输出会占用磁盘空间，定期清理缓存

---

<div align="center">

**如果这个项目对你有帮助，请考虑给它一个 ⭐ Star！**

Made with ❤️ by the Logics-Parsing Team

</div>
