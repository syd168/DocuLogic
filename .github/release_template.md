# Release Notes - v{{VERSION}}

**发布日期**: {{DATE}}

## 🎉 亮点

<!-- 简要介绍本次发布的主要亮点 -->

## ✨ 新功能

<!-- 列出所有新功能 -->

- 
- 
- 

## 🐛 Bug 修复

<!-- 列出所有修复的 bug -->

- 
- 
- 

## 🔧 改进

<!-- 列出所有改进和优化 -->

- 
- 
- 

## 📝 文档

<!-- 列出文档更新 -->

- 
- 
- 

## ⚠️ 破坏性变更

<!-- 如果有破坏性变更，请详细说明 -->

### 迁移指南

<!-- 提供从旧版本迁移的步骤 -->

1. 
2. 
3. 

## 📦 依赖更新

<!-- 列出重要的依赖更新 -->

- 
- 
- 

## 🔐 安全更新

<!-- 如果有安全相关的更新 -->

- 
- 
- 

## 🧪 测试

<!-- 测试相关的变更 -->

- 
- 
- 

## 🚀 部署说明

<!-- 部署时需要注意的事项 -->

### 前置要求

- Python 3.10+
- Node.js 18+
- GPU: （可选，但推荐）

### 升级步骤

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 安装/更新后端依赖
pip install -r requirements.txt

# 3. 安装/更新前端依赖
cd frontend
npm install

# 4. 运行数据库迁移（如果有）
python migrate_xxx.py

# 5. 重启服务
./stop.sh
./start.sh
```

### Docker 部署

```bash
docker-compose pull
docker-compose up -d
```

## 📊 性能指标

<!-- 如果有性能测试数据 -->

- 
- 
- 

## 🙏 致谢

感谢以下贡献者：

- @username1
- @username2

## 📝 完整变更日志

查看完整的 commit 历史：[Compare changes](https://github.com/your-username/Logics-Parsing-Web/compare/v{{PREVIOUS_VERSION}}...v{{VERSION}})

---

**Full Changelog**: https://github.com/your-username/Logics-Parsing-Web/compare/v{{PREVIOUS_VERSION}}...v{{VERSION}}
