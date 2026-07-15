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

Direct 模式直接使用源镜像创建 Template，不会自动注入运行时二进制。用户必须在镜像构建阶段将 `/.fce2b` 放入最终镜像，并在构建请求中设置 Direct 模式请求头。

### 1. 构建 Base 镜像

以下 Dockerfile 基于基础模板所使用的镜像：

```dockerfile
ARG FCE2B_BASE_IMAGE=fc-e2b-registry.cn-hangzhou.cr.aliyuncs.com/runtime/base:v0.0.36
FROM ${FCE2B_BASE_IMAGE} AS fce2b-runtime

FROM docker.io/library/node:20.20-slim AS node

FROM docker.io/library/python:3.13-slim

USER root

RUN sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates git sudo netcat-openbsd \
       build-essential curl wget openssh-client \
       xz-utils patch pkg-config iputils-ping \
    && chmod u+s /usr/bin/ping \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=node /usr/local/include/node /usr/local/include/node

RUN ln -sf /usr/local/bin/python3 /usr/bin/python3 \
    && ln -sf /usr/local/bin/python3 /usr/bin/python \
    && ln -sf /usr/local/bin/pip3 /usr/bin/pip \
    && ln -sf /usr/local/bin/node /usr/local/bin/nodejs \
    && ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -sf /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && ln -sf /usr/local/lib/node_modules/corepack/dist/corepack.js /usr/local/bin/corepack \
    && python3 --version \
    && pip3 --version \
    && node --version \
    && npm --version \
    && corepack --version

RUN corepack enable \
    && corepack prepare yarn@1.22.19 --activate \
    && yarn --version

RUN if id ubuntu >/dev/null 2>&1; then \
        usermod -l user -d /home/user -m ubuntu && \
        groupmod -n user ubuntu; \
    else \
        useradd -m -s /bin/bash -u 1000 user; \
    fi

RUN printf "user ALL=(ALL) NOPASSWD:ALL\nDefaults env_keep += \"PATH\"\nDefaults !secure_path\n" > /etc/sudoers.d/user \
    && chmod 0440 /etc/sudoers.d/user

RUN printf '# Managed by e2b-runtime image-base: ensure /.fce2b in PATH for login shells\ncase ":${PATH}:" in\n    *:/.fce2b:*) ;;\n    *) export PATH="/.fce2b:${PATH}" ;;\nesac\n' > /etc/profile.d/e2b-path.sh \
    && chmod 0644 /etc/profile.d/e2b-path.sh

RUN mkdir -p \
    /etc/sandbox-code-interpreter \
    /var/lib/sandbox \
    /var/log/sandbox \
    /var/log/sandbox-code-interpreter \
    /home/user/workspace \
    /home/user/log \
    /tmp/sandbox/python_contexts \
    && touch /home/user/log/app.log && chmod 666 /home/user/log/app.log \
    && chown -R user:user \
       /var/lib/sandbox \
       /var/log/sandbox \
       /var/log/sandbox-code-interpreter \
       /home/user

ENV SERVICE_MODE=code-interpreter-e2b \
    GATEWAY_LISTEN=0.0.0.0:5000 \
    ENVD_BIN=/.fce2b/envd \
    ENVD_PORT=49983 \
    CODE_INTERPRETER_BIN=/.fce2b/sandbox-code-interpreter \
    CODE_INTERPRETER_PORT=5001

EXPOSE 5000

RUN mkdir -p /home/user/.config/pip \
    && printf '[global]\nindex-url = https://mirrors.aliyun.com/pypi/simple/\ntrusted-host = mirrors.aliyun.com\n' \
       > /home/user/.config/pip/pip.conf \
    && chown -R user:user /home/user/.config

RUN npm config set registry https://registry.npmmirror.com --global 2>/dev/null \
    && echo 'registry=https://registry.npmmirror.com' > /home/user/.npmrc \
    && chown user:user /home/user/.npmrc

WORKDIR /home/user

COPY --from=fce2b-runtime /.fce2b /.fce2b

USER root

ENTRYPOINT ["/.fce2b/entrypoint"]
```

以下设置是必需的：

- 最终容器以 `root` 启动，入口为 `/.fce2b/entrypoint`。
- `ENVD_BIN` 和 `CODE_INTERPRETER_BIN` 指向 `/.fce2b` 中的二进制。
- Gateway 监听 `5000`，envd 监听 `49983`。
- 清空基础镜像继承的 `CMD`，避免它被传给 `fce2b` entrypoint。
- 只构建单一 `linux/amd64` manifest；不要发布 `amd64/arm64` 多架构 index。

构建镜像：

```bash
PUBLIC_IMAGE=<ACR-EE公网地址>/<命名空间>/<仓库>:<不可变tag>

docker buildx build \
  --load \
  --platform linux/amd64 \
  --provenance=false \
  --sbom=false \
  -t "$PUBLIC_IMAGE" \
  .
```

本地验证：

```bash
docker image inspect "$PUBLIC_IMAGE"
docker run --rm --entrypoint /bin/bash "$PUBLIC_IMAGE" -lc '
  test -x /.fce2b/entrypoint
  test -x /.fce2b/envd
  test -x /.fce2b/sandbox-code-interpreter
  case ":$PATH:" in *:/.fce2b:*) ;; *) exit 1;; esac
'
```

### 2. 推送到 ACR 企业版

使用 ACR 企业版公网地址构建和推送镜像；创建 Template 时，使用同一仓库、相同 tag 的 VPC 地址。

```bash
PUBLIC_REGISTRY=<实例公网地址>
VPC_IMAGE=<实例VPC地址>/<命名空间>/<仓库>:<相同tag>

docker login "$PUBLIC_REGISTRY"
docker push "$PUBLIC_IMAGE"
```

推送后确认 tag 正常并记录 digest。

### 3. 以 Direct 模式创建 Template 和 Sandbox

构建 Template 时设置以下请求头：

```text
X-E2B-Template-Build-Mode: direct
```

Python 示例：

```python
from e2b import ApiParams, Sandbox, Template, default_build_logger

API_KEY = "<E2B API Key>"
API_URL = "https://api.cn-hangzhou.e2b.fc.aliyuncs.com"
DOMAIN = "cn-hangzhou.e2b.fc.aliyuncs.com"
VPC_IMAGE = "<ACR-EE VPC endpoint>/<namespace>/<repository>:<immutable tag>"

build_api_params = ApiParams(
    request_timeout=600,
    headers={"X-E2B-Template-Build-Mode": "direct"},
    api_key=API_KEY,
    api_url=API_URL,
    domain=DOMAIN,
)

sandbox_api_params = ApiParams(
    request_timeout=600,
    api_key=API_KEY,
    api_url=API_URL,
    domain=DOMAIN,
)

build = Template.build(
    Template().from_image(VPC_IMAGE),
    name="customer-direct-template",
    cpu_count=2,
    memory_mb=2048,
    on_build_logs=default_build_logger(),
    **build_api_params,
)

sandbox = Sandbox.create(
    template=build.template_id,
    timeout=900,
    **sandbox_api_params,
)

try:
    result = sandbox.commands.run("echo direct-mode-ok", timeout=120)
    print(result.stdout, result.stderr, result.exit_code)
finally:
    sandbox.kill()
```

注意：

- Direct 模式按原样使用 `from_image`，不会创建或推送派生镜像。
- 每次发布使用新的 tag，不要覆盖已经验证通过的镜像 digest。
- 在创建 Sandbox 前等待构建状态变为 `ready`，测试完成后调用 `sandbox.kill()`。

## 构建 Code 镜像

Code 镜像构建在 Base 镜像之上。Base 镜像已包含兼容 Function Compute E2B 的二进制，因此 Code 镜像不需要再次注入它们。

```dockerfile
ARG RUNTIME_BASE_IMAGE=<ACR-EE-public-endpoint>/<namespace>/<repository>:<immutable-tag>
FROM ${RUNTIME_BASE_IMAGE}

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libgl1 libglib2.0-0 libsndfile1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --break-system-packages --no-cache-dir \
       --index-url https://mirrors.aliyun.com/pypi/simple/ \
       --trusted-host mirrors.aliyun.com \
       --retries 20 \
       --timeout 120 \
       --prefer-binary \
       pandas \
       numpy \
       matplotlib \
       scipy \
       scikit-learn \
       seaborn \
       plotly \
       ipykernel \
       jupyter_client \
       bokeh \
       pillow \
       opencv-python \
       nltk \
       spacy \
       librosa \
    && python3 -c "import pandas, numpy, matplotlib, scipy, sklearn, seaborn, plotly, ipykernel, jupyter_client, bokeh, PIL, cv2, nltk, spacy, librosa; print('core data science stack OK')"

RUN node --version \
    && npm --version \
    && corepack --version \
    && yarn --version
```
