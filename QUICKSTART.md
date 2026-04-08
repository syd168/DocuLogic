# DocuLogic 快速开始指南

<div align="center">

**⚡ 3分钟快速启动智能文档解析平台**

</div>

---

## 🎯 选择你的部署方式

### 🐳 Docker 部署（推荐新手）

```bash
# 一行命令搞定
git clone https://github.com/your-username/DocuLogic.git && cd DocuLogic && ./docker/deploy.sh

# 访问: http://localhost
# 账号: admin / admin123
```

**优点：**
- ✅ 一键部署，无需配置
- ✅ 自动处理依赖
- ✅ 生产环境就绪
- ✅ 支持 GPU 加速

**要求：**
- Docker 20.10+
- Docker Compose v2.0+
- 8GB+ 内存

---

### 💻 本地部署（推荐开发者）

```bash
# 1. 克隆项目
git clone https://github.com/your-username/DocuLogic.git
cd DocuLogic

# 2. 下载模型
python logics-parsingv2/download_model_v2.py

# 3. 安装依赖
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，设置 MODEL_PATH

# 5. 启动服务
./start.sh

# 访问: http://localhost:5173
```

**优点：**
- ✅ 便于调试和开发
- ✅ 实时热重载
- ✅ 完整源代码访问

**要求：**
- Python 3.10+
- Node.js 16+
- 16GB+ 内存

---

## 📋 部署后检查清单

### 1. 验证服务状态

```bash
# Docker 部署
docker ps | grep doculogic
curl http://localhost/health

# 本地部署
ps aux | grep python
curl http://localhost:8000/health
```

### 2. 登录系统

- 访问前端界面
- 使用默认账号登录：`admin / admin123`
- **立即修改密码！**

### 3. 测试文档解析

1. 上传一个测试 PDF 或图片
2. 等待解析完成
3. 查看结果是否正确

### 4. 检查日志

```bash
# Docker
docker logs -f doculogic

# 本地
tail -f logs/app.log
```

---

## 🔧 常用操作速查

### 启动/停止

```bash
# Docker
docker compose up -d          # 启动
docker compose down           # 停止
docker compose restart        # 重启

# 本地
./start.sh                    # 启动
./stop.sh                     # 停止
```

### 查看日志

```bash
# Docker
docker logs -f doculogic      # 实时日志
docker logs --tail 100 doculogic  # 最近100行

# 本地
tail -f logs/app.log
```

### 更新版本

```bash
# Docker
git pull && ./docker/deploy.sh

# 本地
git pull
pip install -r requirements.txt
cd frontend && npm install
```

### 备份数据

```bash
# Docker
docker cp doculogic:/app/data/database/app.db ./backup.db

# 本地
cp web/data/app.db ./backup.db
```

---

## ❓ 遇到问题？

### 容器启动失败

```bash
# 查看详细错误
docker logs doculogic

# 检查模型文件
ls -lh ~/doculogic/weights/Logics-Parsing-v2/

# 重新部署
./docker/deploy.sh
```

### 端口被占用

```bash
# 查看占用进程
sudo lsof -i :80

# 修改端口
echo "HOST_PORT=8080" >> docker/.env
docker compose up -d
```

### GPU 无法识别

```bash
# 验证 GPU 支持
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# 重新配置
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 内存不足

```bash
# 增加 swap（Ubuntu）
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📚 更多资源

- 📖 **完整文档**：[README.md](README.md)
- 🐳 **Docker 指南**：[docker/README.md](docker/README.md)
- 🔧 **Redis 实施**：[REDIS_IMPLEMENTATION_PLAN.md](REDIS_IMPLEMENTATION_PLAN.md)
- 🐛 **报告问题**：[GitHub Issues](https://github.com/your-username/DocuLogic/issues)

---

## 🎉 开始使用

现在你已经成功部署 DocuLogic，可以：

1. 📤 **上传文档** - 支持 PDF、PNG、JPG 等格式
2. ⚙️ **调整设置** - 配置 PDF 页数、输出模式等
3. 👥 **管理用户** - 创建和管理用户账户
4. 📊 **查看结果** - 下载 Markdown、可视化结果
5. 🔧 **系统管理** - 监控任务、清理缓存

**祝你使用愉快！** 🚀

---

<div align="center">

需要帮助？查看 [docker/README.md](docker/README.md) 获取详细指南

Made with ❤️ by the DocuLogic Team

</div>
