# 内置 Template Dockerfile

本文说明自定义 E2B Template 镜像的镜像与仓库要求，以及 Builder 和 Direct 两种构建模式。完整英文版及完整 Dockerfile/Python 示例见 [Direct-Mode E2B Template Dockerfile](./direct-mode-e2b-template-dockerfile.md)。

## 官方文档

<https://help.aliyun.com/zh/functioncompute/build-a-custom-image-template>

## 镜像要求

- 使用 AMD64 架构的 Linux 镜像。
- 构建时关闭 provenance，例如：`docker build --platform=linux/amd64 --provenance=false -t <镜像:标签> .`。
- 推荐 Ubuntu 20.04、Debian 12（bookworm）及以上系统。

## 镜像仓库要求

- 在与云沙箱相同 UID、相同地域下创建 ACR 企业版实例；经济版暂不支持。
- ACR 企业版实例至少绑定一个 VPC。
- VPC 下至少有一个 vSwitch 位于函数计算支持的可用区。
- 配置 ACR 访问控制和 VPC 网络，使对应网络可以访问实例。
- VPC 网段必须使用 RFC 1918 私有地址：`10.0.0.0/8`、`172.16.0.0/12` 或 `192.168.0.0/16`。
- VPC 中需要至少一个非云服务托管的安全组，并在规则中允许访问 ACR 企业版实例。

## Builder 模式

Template Build 会在源镜像上增加一层并生成新的镜像 tag，同时注入符合 E2B 运行时协议所需的官方二进制文件。

## Direct 模式

Direct 模式直接使用源镜像创建 Template，不会自动注入运行时二进制。用户必须在镜像构建阶段将 `/.fce2b` 放入最终镜像，并在构建请求中传入：

```text
X-E2B-Template-Build-Mode: direct
```

## Base 镜像要求

- 最终容器以 `root` 启动，入口为 `/.fce2b/entrypoint`。
- `ENVD_BIN` 和 `CODE_INTERPRETER_BIN` 指向 `/.fce2b` 中的二进制。
- Gateway 监听 `5000`，envd 监听 `49983`。
- 清空基础镜像继承的 `CMD`，避免它被传给 `fce2b` entrypoint。
- 只构建单一 `linux/amd64` manifest；不要发布 `amd64/arm64` 多架构 index。

构建示例：

```bash
PUBLIC_IMAGE=<ACR-EE公网地址>/<命名空间>/<仓库>:<不可变tag>
docker buildx build --load --platform linux/amd64 --provenance=false --sbom=false -t "$PUBLIC_IMAGE" .
```

构建后应检查 `/.fce2b/entrypoint`、`/.fce2b/envd`、`/.fce2b/sandbox-code-interpreter` 可执行，且登录 shell 的 `PATH` 包含 `/.fce2b`。

## 推送与创建 Template

使用 ACR 企业版公网地址登录和推送镜像；创建 Template 时，使用同一仓库、相同 tag 的 VPC 地址。推送完成后确认 tag 正常并记录 digest。

构建请求设置 `X-E2B-Template-Build-Mode: direct` 后，使用 `Template().from_image(VPC_IMAGE)` 调用 `Template.build`。等待构建状态为 `ready` 后再创建 Sandbox，并在测试结束后调用 `sandbox.kill()`。

## Code 镜像

Code 镜像基于已注入 `/.fce2b` 的 Base 镜像，因此不需要重复注入运行时。可在此层安装数据科学或多媒体依赖，例如 `pandas`、`numpy`、`matplotlib`、`scipy`、`scikit-learn`、`opencv-python`、`spacy` 和 `librosa`。完整的 Base/Code Dockerfile 与 Python 示例保留在英文对照版中。
