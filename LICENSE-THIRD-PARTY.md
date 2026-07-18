# 第三方组件与许可证说明

DocuLogic 本体采用 [Apache License 2.0](LICENSE)。以下组件为**可选**依赖，**默认不随主发行物捆绑安装**。

## Marker（可选文档解析引擎）

| 项 | 说明 |
|----|------|
| 组件 | [marker-pdf](https://github.com/VikParuchuri/marker)（Datalab / Vik Paruchuri） |
| 接入方式 | `converts/plugins/marker/` 适配插件 + `pip install -r requirements-marker.txt` |
| 代码许可 | **GPL-3.0-or-later** |
| 模型许可 | **OpenRAIL-M**（及上游 surya 等相关权重条款，以官方仓库为准） |
| 商业使用 | 代码 GPL 具有传染性；模型 OpenRAIL-M 对商业规模有额外限制。闭源分发或商业产品请自行评估或联系 [Datalab](https://www.datalab.to/pricing) 获取商业授权 |

### 合规实践（本项目约定）

1. **默认不安装**：`requirements.txt` 与默认 Docker 镜像不包含 `marker-pdf`。
2. **用户显式启用**：仅在执行 `pip install -r requirements-marker.txt`（或等价操作）后可用。
3. **不提交上游源码**：`converts/models/marker` 若存在仅为本地参考，已由 `.gitignore` 排除，不进入 GitHub 发行。
4. **启用即接受条款**：使用 Marker 解析器即表示接受其 GPL / OpenRAIL 等上游许可。

### 安装

```bash
pip install -r requirements-marker.txt
# 重启后端后，管理后台「切换解析器」可选 Marker
```

本文件仅为项目披露与实践说明，**不构成法律意见**。
