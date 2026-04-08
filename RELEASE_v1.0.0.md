# DocuLogic v1.0.0 发布说明

**发布日期**: 2026-04-08  
**版本类型**: 首个正式版本 (Major Release)

---

## 🎉 概述

DocuLogic v1.0.0 是首个正式发布的稳定版本，提供完整的企业级智能文档解析解决方案。该版本基于阿里巴巴开源的 Logics-Parsing-v2 模型，集成了用户管理、会话控制、多数据库支持和完善的部署方案。

## ✨ 核心功能

### 1. 完整的用户认证系统
- ✅ 邮箱/手机号注册与登录
- ✅ 图形验证码防暴力破解
- ✅ 找回密码功能（邮件/SMS）
- ✅ 密码强度校验与复杂度要求
- ✅ JWT Token 认证机制

### 2. 单点登录 (SSO)
- ✅ Token 黑名单机制（Redis）
- ✅ 多终端互斥登录
- ✅ 管理员强制踢出用户
- ✅ 会话管理与追踪
- ✅ 自动清理过期会话

### 3. 多数据库支持
- ✅ SQLite（开发环境默认）
- ✅ MySQL 8.0+（生产环境推荐）
- ✅ 无缝切换，无需修改代码
- ✅ 自动数据库迁移
- ✅ 数据持久化与备份

### 4. Redis 缓存集成
- ✅ 验证码存储（6位数字）
- ✅ 速率限制（防刷）
- ✅ Token 黑名单
- ✅ 会话管理
- ✅ 降级策略（Redis 不可用时自动切换到数据库）

### 5. Docker 一键部署
- ✅ 多阶段构建优化镜像体积
- ✅ Nginx 反向代理
- ✅ GPU 加速支持（可选）
- ✅ 自动化部署脚本
- ✅ 健康检查与自动重启

### 6. 管理后台
- ✅ 系统设置动态配置
- ✅ 用户管理（CRUD + 批量操作）
- ✅ 任务查询与清理
- ✅ 模型下载与重载
- ✅ 实时监控与日志

## 🐛 Bug 修复

- 修复环境变量解析时行尾注释导致的问题
- 修复 Token 解码失败时的错误处理逻辑
- 修复系统设置初始化值为 0 的问题
- 修复 Docker 容器中 MySQL 用户权限问题
- 修复 PDF.js Worker 加载失败的问题
- 修复 deploy.sh 中目录切换路径错误

## 🔧 优化改进

### 性能优化
- 优化数据库迁移逻辑，支持增量更新
- 优化 Docker 镜像构建速度（多阶段构建）
- 优化前端加载性能（代码分割）
- 优化模型加载流程（异步加载）

### 用户体验
- 优化日志输出，区分不同级别的信息
- 优化错误提示，提供更友好的用户反馈
- 优化 WebSocket 实时进度推送
- 优化表单验证和输入提示

### 安全性
- 增强密码哈希算法（bcrypt）
- 添加 CSRF 保护
- 添加 CORS 配置
- 添加速率限制（防 DDoS）

## 📝 文档完善

- 重写 README.md，增加架构图和 API 文档
- 添加详细的 Docker 部署说明
- 添加常见问题解答 (FAQ)
- 添加 API 使用示例（curl 命令）
- 添加技术栈说明和性能指标

## 🏗️ 技术栈

### 后端
- **框架**: FastAPI 0.100+
- **ORM**: SQLAlchemy 2.0
- **认证**: JWT (python-jose) + bcrypt
- **缓存**: Redis 7.x
- **WebSocket**: 实时进度推送
- **数据库**: MySQL 8.0 / SQLite 3

### 前端
- **框架**: Vue 3 + Composition API
- **UI库**: Element Plus
- **路由**: Vue Router 4
- **状态管理**: Pinia
- **HTTP客户端**: Axios
- **构建工具**: Vite 5

### 基础设施
- **容器化**: Docker + Docker Compose
- **Web服务器**: Nginx
- **AI模型**: Logics-Parsing-v2
- **深度学习**: PyTorch 2.0+

## 📊 性能指标

- **OmniDocBench-v1.5**: 总体得分 93.23
- **LogicsDocBench**: 总体得分 82.16
- **支持文档类型**: 9 大类、20+ 小类
- **解析速度**: GPU 模式下平均 2-5 秒/页

## 🚀 快速开始

### Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/your-username/DocuLogic.git
cd DocuLogic

# 2. 一键部署
./docker/deploy.sh

# 3. 访问应用
# http://localhost:8030
# 默认账号: admin / admin123
```

### 本地开发

```bash
# 1. 安装依赖
pip install -r requirements.txt
cd frontend && npm install

# 2. 启动服务
./start.sh

# 3. 访问应用
# 前端: http://localhost:5173
# API: http://localhost:8000/api/docs
```

## 📦 下载

- **源代码**: [GitHub Releases](https://github.com/your-username/DocuLogic/releases/tag/v1.0.0)
- **Docker 镜像**: `docker pull your-username/doculogic:v1.0.0`（待发布）
- **模型权重**: [HuggingFace](https://huggingface.co/Logics-MLLM/Logics-Parsing-v2)

## 🔐 安全建议

1. **修改默认密码**: 首次登录后立即修改 admin 密码
2. **生成强密钥**: 使用 `openssl rand -hex 32` 生成 JWT_SECRET
3. **启用 HTTPS**: 生产环境务必配置 SSL 证书
4. **配置防火墙**: 仅开放必要端口（8030）
5. **定期备份**: 备份 MySQL 数据库和解析结果
6. **更新依赖**: 定期检查并更新 Python/Node.js 依赖

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 Apache 2.0 许可证。详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [Logics-Parsing-v2](https://github.com/alibaba/Logics-Parsing) - 阿里巴巴开源的文档解析模型
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Python Web 框架
- [Vue 3](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Element Plus](https://element-plus.org/) - Vue 3 组件库

## 📧 联系方式

- **项目主页**: [GitHub Repository](https://github.com/your-username/DocuLogic)
- **问题反馈**: [Issues](https://github.com/your-username/DocuLogic/issues)
- **模型主页**: [HuggingFace](https://huggingface.co/Logics-MLLM/Logics-Parsing-v2)

---

<div align="center">

**感谢所有为 DocuLogic v1.0.0 做出贡献的开发者！**

Made with ❤️ by the DocuLogic Team

</div>
