# E2B Code Interpreter 示例

[English](README.md)

一个使用阿里云 E2B Code Interpreter SDK 的最小示例：创建 Sandbox、在其中运行 Python 代码，并销毁 Sandbox。

## 功能

1. **创建 Sandbox**：启动带有 Python 解释器的隔离云环境。
2. **计算圆面积**：运行 Python 代码计算半径为 5 的圆面积。
3. **计算周长**：在同一 Sandbox 中继续运行代码，通过读取第一次执行保存的半径展示状态持久化。
4. **销毁 Sandbox**：释放全部资源。

## 快速开始

```bash
# 1. 创建虚拟环境
uv venv .venv --python 3.12
source .venv/bin/activate

# 2. 安装依赖
uv pip install -r requirements.txt

# 3. 配置环境变量
cp env.example .env
# 编辑 .env，填写 E2B_API_KEY、E2B_API_URL 和 E2B_DOMAIN。

# 4. 运行示例
python code_exec.py
```

## 环境变量

E2B SDK 会自动读取以下变量，无需在代码中显式传递。

| 变量 | 必填 | 说明 |
|---|---|---|
| `E2B_API_KEY` | 是 | 阿里云 E2B API Key。 |
| `E2B_API_URL` | 是 | 阿里云 E2B 控制面 API URL。 |
| `E2B_DOMAIN` | 是 | 阿里云 E2B Sandbox 域名。 |

## SDK 用法（最小示例）

```python
from e2b_code_interpreter import Sandbox

sbx = Sandbox.create()
execution = sbx.run_code("""
import math
radius = 5
area = math.pi * radius ** 2
print(f"Area: {area:.2f}")
""")
print(execution.logs.stdout)
sbx.kill()
```

## 项目结构

```text
e2b-code-interpreter/
├── code_exec.py      # 主示例脚本（约 50 行）
├── env.example       # .env 模板
├── pyproject.toml    # 项目元数据和依赖
├── requirements.txt  # 固定版本的依赖
└── README.md
```
