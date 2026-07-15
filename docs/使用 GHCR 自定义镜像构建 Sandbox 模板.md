# 使用 GHCR 私有镜像构建 Sandbox 模板

云沙箱支持直接从容器镜像仓库拉取镜像来构建 Sandbox 模板。将特定语言运行时、系统依赖、私有 SDK 或数据科学工具链预置在镜像中，再从镜像构建模板，比在运行时逐条安装依赖更可控、可复现。

本文说明如何在美国（硅谷）地域（`us-west-1`）使用 GHCR 私有镜像 `ghcr.io/<owner>/<image>:<tag>` 构建模板、创建 Sandbox 并完成运行校验。完整英文版见 [Build a Sandbox Template from a Private GHCR Image](./ghcr-private-image-sandbox-template.md)。

## 业务场景

- 团队将统一的 Python/Node 运行时和常用依赖打包为镜像，供多个 Agent 复用。
- 在构建期一次安装 `pandas`、`numpy`、绘图库等重依赖，避免每次任务运行时安装。
- 使用仅发布在 GHCR 私有仓库中的 SDK 或内部工具。
- 让镜像版本与模板版本对齐，支持追溯和回滚。

## 前置条件

- 已开通云沙箱，并获取目标地域的 `E2B_API_KEY`。
- 美国（硅谷）地域接入点：
  - `api_url`：`https://api.us-west-1.e2b.fc.aliyuncs.com`
  - `domain`：`us-west-1.e2b.fc.aliyuncs.com`
- 已准备 GHCR 镜像，例如 `ghcr.io/<owner>/python:3.10`。
- 已准备镜像拉取凭据。
- 已安装 SDK：`pip install e2b`。

## 镜像仓库凭据

从 GHCR 私有仓库拉取镜像时，使用 GitHub 的 [Personal Access Token (classic)](https://github.com/settings/tokens)，而不是账号密码：

- **用户名**：镜像 owner 的 GitHub 用户名。
- **密码**：Personal Access Token (classic)。

Token 至少需要 `read:packages`；创建时可同时选择 `write:packages`。缺少包权限会在构建拉取镜像时导致 401 或 403。通过 GitHub 的 **Settings → Developer settings → Personal access tokens → Tokens (classic)** 创建。

通过 SDK 的 `headers` 参数传入凭据：

| Header | 含义 |
| --- | --- |
| `X-E2B-Template-Source-Username` | GitHub 用户名 |
| `X-E2B-Template-Source-Password` | Personal Access Token (classic) |

> 凭据属于敏感信息。请通过环境变量或密钥管理服务注入，不要硬编码或提交到仓库。

## 推荐流程

1. 用 `Template().from_image(<镜像地址>)` 声明镜像来源，并通过 `headers` 提供仓库凭据。
2. 调用 `Template.build` 构建模板，设置 `cpu_count`、`memory_mb` 等规格，并保存 `template_id`。
3. 用 `template_id` 创建 Sandbox，等待数据面就绪后运行冒烟测试。
4. 校验完成后销毁 Sandbox。

模板构建是一次性动作。同一个 `template_id` 可供后续多次 `Sandbox.create` 复用；生产环境应将构建与运行分为两个阶段。

## 示例

以下命令将凭据放在环境变量中：

```bash
export USERNAME="<github-username>"
export PASSWORD="ghp_xxxxxxxxxxxxxxxxxxxx"
export E2B_API_KEY="<your-e2b-api-key>"
python3 build_from_ghcr.py
```

对应的完整 Python 示例（模板构建、Sandbox 创建、就绪重试、校验和销毁）见英文版的 [Example](./ghcr-private-image-sandbox-template.md#example) 章节。运行成功时会输出构建日志、`template_id`、`sandbox_id` 和 `sandbox-ok`，最后销毁 Sandbox。

## 上线建议

- 通过环境变量或密钥服务管理 GitHub Token 与 `E2B_API_KEY`，遵循最小权限并定期轮转。
- 持久化并复用构建产物 `template_id`，不要在每次运行前重复构建。
- 使用明确、不可变的镜像 tag，而不是只依赖 `latest`。
- 按工作负载选择 `cpu_count` 与 `memory_mb`；重依赖或大数据场景需要更高规格。
- 将 `sandbox.kill()` 放在 `finally` 中，避免异常路径遗留资源。
