# Direct-Mode E2B Template Dockerfile

This guide describes image prerequisites, registry networking requirements, and Dockerfile examples for building custom E2B-compatible template images. It covers both Builder mode and Direct mode, with a focus on preparing a reusable base image and a data-science code image.

## Official documentation

<https://help.aliyun.com/zh/functioncompute/build-a-custom-image-template>

## Image requirements

- Use an AMD64 Linux image.
- Disable provenance metadata when building the image. See [Custom image deployment fails with platform `unknown/unknown`](https://help.aliyun.com/zh/functioncompute/fc/custom-image-deployment-fails-with-platform-of-image-is-unknown-unknown). For example: `docker build --platform=linux/amd64 --provenance=false -t <image:tag> .`.
- Recommended base operating systems: Ubuntu 20.04, Debian 12 (bookworm), or later.

## Registry requirements

- Create an ACR Enterprise Edition instance under the same account and in the same region as Cloud Sandbox. The Economy Edition is not supported.
- Bind at least one VPC to the ACR Enterprise Edition instance.
- Ensure the VPC has at least one vSwitch in an availability zone supported by Function Compute.
- Configure ACR access control and VPC networking to allow access from the relevant network.
- Use an RFC 1918 private range for the VPC: `10.0.0.0/8`, `172.16.0.0/12`, or `192.168.0.0/16`. Public-address ranges used privately are not supported; see the VPC FAQ.
- Configure at least one non-cloud-service-managed security group in the VPC, and allow access to the ACR Enterprise Edition instance in its rules.

## Builder mode

Template Build adds a layer to the source image, producing a new image tag. It injects the official binaries required to run the image under the E2B runtime protocol.

## Direct mode

Template Build uses the source image directly. You must provide the required runtime binaries in the image yourself. The same approach can later be used to customize your own `envd` and `code-interpreter` components.

Direct mode does not inject Function Compute E2B runtime binaries. During image construction, copy `/.fce2b` into the final image and then set the Direct-mode header so the platform uses that image directly.

### 1. Build the base image

The following Dockerfile is based on the image used by the base template:

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

The following settings are mandatory:

- Start the final container as `root` and use `/.fce2b/entrypoint` as its entrypoint.
- Point `ENVD_BIN` and `CODE_INTERPRETER_BIN` to binaries in `/.fce2b`.
- Listen on port `5000` for the gateway and port `49983` for envd.
- Clear any inherited base-image `CMD`, so it is not passed as an argument to the `fce2b` entrypoint.
- Build a single `linux/amd64` manifest. Do not publish an `amd64/arm64` multi-architecture index.

Build the image:

```bash
PUBLIC_IMAGE=<ACR-EE-public-endpoint>/<namespace>/<repository>:<immutable-tag>

docker buildx build \
  --load \
  --platform linux/amd64 \
  --provenance=false \
  --sbom=false \
  -t "$PUBLIC_IMAGE" \
  .
```

Verify it locally:

```bash
docker image inspect "$PUBLIC_IMAGE"
docker run --rm --entrypoint /bin/bash "$PUBLIC_IMAGE" -lc '
  test -x /.fce2b/entrypoint
  test -x /.fce2b/envd
  test -x /.fce2b/sandbox-code-interpreter
  case ":$PATH:" in *:/.fce2b:*) ;; *) exit 1;; esac
'
```

### 2. Push to ACR Enterprise Edition

Build and push with the public ACR Enterprise Edition endpoint; use the VPC endpoint for the same repository when creating the template.

```bash
PUBLIC_REGISTRY=<instance-public-endpoint>
VPC_IMAGE=<instance-vpc-endpoint>/<namespace>/<repository>:<same-tag>

docker login "$PUBLIC_REGISTRY"
docker push "$PUBLIC_IMAGE"
```

After pushing, confirm that the tag is healthy and record its digest.

### 3. Create a Template and Sandbox in Direct mode

Set one request header when building the template:

```text
X-E2B-Template-Build-Mode: direct
```

Python example:

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

Notes:

- Direct mode uses `from_image` as-is; it does not create or push a derived image.
- Use a new tag for every release. Do not overwrite an image digest that has already passed validation.
- Wait until the build is `ready` before creating a Sandbox, and call `sandbox.kill()` after testing.

## Build a code image

A code image builds on the base image. Because the base image already includes the Function Compute E2B-compatible binaries, the code image does not need to inject them again.

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
