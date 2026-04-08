# DocuLogic Docker 部署

## 快速启动

```bash
cd docker
docker compose up -d --build
```

访问：http://localhost:8030  
默认账号：admin / admin123

## 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `HOST_PORT` | 访问端口 | `8030` |
| `DATA_DIR` | 数据目录 | `~/doculogic/data` |
| `MODEL_DIR` | 模型目录 | `~/doculogic/models` |
| `GPU_COUNT` | GPU数量（0=禁用） | `0` |
| `JWT_SECRET` | JWT密钥 | `change-me-in-production` |
| `MEM_LIMIT` | 内存限制 | `8g` |
| `CPU_LIMIT` | CPU限制 | `4.0` |

### 使用示例

```bash
# 自定义端口
HOST_PORT=8080 docker compose up -d

# 启用GPU
GPU_COUNT=1 docker compose up -d

# 自定义数据路径
DATA_DIR=/my/data MODEL_DIR=/my/models docker compose up -d
```

## 数据目录

```
~/doculogic/
├── data/
│   ├── output/      # 解析输出
│   ├── logs/        # 日志
│   └── database/    # 数据库
└── models/          # 模型权重
```

## 常用命令

```bash
# 启动
docker compose up -d

# 停止
docker compose down

# 查看日志
docker logs -f doculogic

# 重启
docker compose restart

# 重新构建
docker compose up -d --build
```
