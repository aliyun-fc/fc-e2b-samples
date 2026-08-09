# envd 移植到你自己的镜像（含完整源码）

> 本文讲怎么把 e2b 的 envd 移植进一个从零搭建的自定义镜像，源码都在 `e2b-custom-image/`。
> 从「有 process-compose 吗 / 有进程听 5000 吗 / 有 SDK 默认用户吗」三个岔口出发，逐条补齐缺的部分。

**目录**

- [envd 移植到你自己的镜像（含完整源码）](#envd-移植到你自己的镜像含完整源码)
  - [1. 没有 process-compose：用 supervisord 托管 envd](#1-没有-process-compose用-supervisord-托管-envd)
  - [2. 没有 5000 上的多端口反代：加一层 openresty](#2-没有-5000-上的多端口反代加一层-openresty)
  - [3. SDK 默认用户 `user`：自定义镜像必须自己建](#3-sdk-默认用户-user自定义镜像必须自己建)
  - [4. 从零搭镜像的四个坑](#4-从零搭镜像的四个坑)
  - [5. 移植检查表](#5-移植检查表)
  - [附录：文件清单](#附录文件清单)

---

```mermaid
flowchart TD
    A["你的镜像"] --> B{"有 process-compose 吗？"}
    B -->|有| B1["加一份 process-compose.envd.yaml<br/>fork entrypoint 加一行"]
    B -->|"没有<br/>（自己的 entrypoint）"| B2["supervisord 托管 envd<br/>autorestart=true"]
    B1 --> C{"容器内有进程监听 5000 吗？"}
    B2 --> C
    C -->|有 nginx/openresty| C1{"它做多端口转发吗？"}
    C -->|"没有"| C2["加一层 openresty<br/>listen 5000 + 多端口路由"]
    C1 -->|做| D{"有 SDK 默认用户 user 吗？"}
    C1 -->|不做| C3["补多端口路由配置"]
    C2 --> D
    C3 --> D
    D -->|有| OK["✅ 可用"]
    D -->|"没有<br/>（多为自定义镜像）"| D1["建 uid 1000 的 user 账号"]
    D1 --> OK

    style OK stroke-width:3px
```

下面每条结论都在 `e2b-custom-image/` 上实测过：`debian:bookworm-slim` 起步，
自己装 openresty、自己写多端口路由、自己用 supervisord 托管 envd，
完整跑通 build、本地验证、push、模板构建、创建沙箱，`commands.run` / `files` 都能用。
成品镜像 235MB。

文件清单见 [附录：文件清单](#附录文件清单)，源码就在本目录，直接打开对应文件即可。

## 1. 没有 process-compose：用 supervisord 托管 envd

关键只有一条：envd 必须常驻，挂了要自动拉起。它一挂，整个沙箱的 E2B SDK 某些能力就没了。
不必为此引入 process-compose，交给 supervisord 就够。

```dockerfile
COPY --from=envd-extract /.fce2b/envd /usr/local/bin/envd
RUN apt-get update && apt-get install -y --no-install-recommends supervisor \
    && rm -rf /var/lib/apt/lists/*
COPY supervisor-envd.conf /etc/supervisor/conf.d/10-envd.conf
```

`supervisor-envd.conf` 如下。镜像本来就在用 supervisord 的话，集成 envd 就只有这一个 `COPY`，
主配置和其他进程定义一行都不用动：

```ini
[program:envd]
command=/usr/local/bin/envd
autostart=true
autorestart=true
; 存活 1s 以上才算启动成功
startsecs=1
; supervisord 没有「无限重试」，给一个大到不可能耗尽的值（见下方警告）
startretries=1000000
stopsignal=TERM
stopwaitsecs=10
; 连同 envd fork 出来的子进程（commands.run 起的用户进程）一起收掉
stopasgroup=true
killasgroup=true
priority=10
; 日志转发到容器 stdout，不落盘（沙箱是临时的）
redirect_stderr=true
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
```

> **`autorestart=true` 一条不够，必须同时改 `startretries`。**
> supervisord 的默认值是 `startretries=3`：envd 连续快速失败 3 次后进入 **FATAL 并永不再拉起**，
> 正是 process-compose 的 `restart: always` 明确要避免的语义。
> 实测（`/bin/false` + `autorestart=true` + `startretries=3`）：
> ```
> t+1s   crashy   BACKOFF   Exited too quickly
> t+4s   crashy   FATAL     Exited too quickly     ← 之后再不重试
> ```
> 表现会是「沙箱前几分钟好的，之后所有 SDK 调用 502」，极难排查。

从零搭的镜像还要写主配置。三个要点：

```ini
[supervisord]
; 前台运行：容器里必须，否则 PID 1 秒退、容器直接结束
nodaemon=true
logfile=/dev/null
logfile_maxbytes=0

; unix socket：沙箱里一条 `supervisorctl status` 就能看出谁挂了、重启过几次
[unix_http_server]
file=/var/run/supervisor.sock
chmod=0700

[supervisorctl]
serverurl=unix:///var/run/supervisor.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[include]
files = /etc/supervisor/conf.d/*.conf
```

entrypoint 只剩目录准备 + 一行 `exec`，里面**不再有任何进程管理逻辑**：

```bash
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf -n
```

用 `exec` 而不是后台起 + `wait`：让 supervisord 当 PID 1，容器的 TERM/INT 才到得了它，
子进程的信号转发和僵尸回收也一并由它负责。

**三个 supervisord 特有的坑：**

| 坑 | 后果 |
|---|---|
| 写了行尾 `; 注释` | supervisord **不剥行尾注释**，`autorestart=true  ; 自动重启` 的值会变成 `true  ; 自动重启`。只用整行注释 |
| 反代忘了 `daemon off;` | openresty 一启动就 fork 到后台，supervisord 以为它秒退，反复重启 |
| socket `chmod=0700` | `supervisorctl` 只有 root 能用，这是故意的：否则沙箱里的 `user` 能 `supervisorctl stop envd` 停掉 root 起的进程。SDK 侧要查状态得 `commands.run(..., user="root")` |

构建期护栏：supervisord 没有 `nginx -t` 那样的 dry-run，用 `configparser`
按它自己的解析规则（不剥行尾注释）读一遍，断言关键值就是字面上那几个，
顺带把上面第一个坑也挡住了：

```dockerfile
RUN python3 -c "import configparser, glob; \
cp = configparser.ConfigParser(interpolation=None); \
cp.read(['/etc/supervisor/supervisord.conf'] + sorted(glob.glob('/etc/supervisor/conf.d/*.conf'))); \
assert cp.get('supervisord', 'nodaemon') == 'true'; \
assert cp.get('program:envd', 'command') == '/usr/local/bin/envd'; \
assert cp.get('program:envd', 'autorestart') == 'true'; \
assert int(cp.get('program:envd', 'startretries')) >= 1000000"
```

> 验收要验「崩了能起来」，不能只验「现在在跑」。`verify-local.sh` 第 ⑦ 项：
> `pkill -9 -f /usr/local/bin/envd` 之后 6 秒内 49983 重新在听，且
> `supervisorctl status envd` 回到 **RUNNING**（不是 FATAL/BACKOFF）。
> 后半句不能省：进 FATAL 之前 supervisord 也会重启几次，只看端口会漏判。
>
> 反过来，判 `RUNNING` 要轮询，不能采样一次：`startsecs=1` 未满时状态是 `STARTING`，
> 沙箱恢复很快，首个命令经常就落在这 1 秒内，实测就踩过。
> 采样一次会把正常的 `STARTING` 误判成失败。`BACKOFF` 同理是过渡态，
> 只有 `RUNNING` / `FATAL` / `EXITED` 是终态。

## 2. 没有 5000 上的多端口反代：加一层 openresty

必须是 openresty，不是 nginx：多端口路由用到 `rewrite_by_lua_block` / `ngx.exec`，
Debian/Ubuntu 仓库里的 `nginx` 包没有 lua 模块。从零装：

```dockerfile
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl gnupg; \
    curl -fsSL https://openresty.org/package/pubkey.gpg \
        | gpg --dearmor -o /usr/share/keyrings/openresty.gpg; \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/openresty.gpg] \
http://openresty.org/package/debian bookworm openresty" \
        > /etc/apt/sources.list.d/openresty.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends openresty; \
    apt-get purge -y --auto-remove gnupg; \
    rm -rf /var/lib/apt/lists/*
```

装出来的配置根目录是 `/etc/openresty/`（不是 `/etc/nginx/`），二进制是
`/usr/local/openresty/bin/openresty`。它默认不带 `nginx.conf` 里的
`client_body_temp` 等临时目录，得自己 `mkdir`（ 放在 `/var/lib/openresty/` 下，
并用 `-p` 指定 prefix）。

`nginx.conf` 的 server 块：

```nginx
server {
    listen 0.0.0.0:5000;      # ① 网关只认 5000
    server_name _;
    include conf.d/*.conf;    # 多端口路由 + 你自己的业务路由
}
```

`http` 块级（放 `http.d/00-multiport.conf` 之类，被 `include` 进 http 块）：

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

# 让 rewrite_by_lua 先于 ngx_rewrite 的 return/rewrite 执行，
# 否则 envd 的 /health 会被你自己的 `location = /health { return 200 ... }` 抢先应答
rewrite_by_lua_no_postpone on;
```

`server` 块级（放 `conf.d/00-multiport-routes.conf`，注意 `00-` 前缀保证先被 include）：

```nginx
set $target_port "";

# 放在 server 级 → 所有 location 继承 → 带端口前缀的请求能在
# location = /health、location ~ ^/api/ 这些精确/前缀路由之前被劫持
rewrite_by_lua_block {
    local port = ngx.var.http_x_sandbox_port
    if not port or port == "" then
        port = string.match(ngx.var.host or "", "^(%d+)%-")
    end
    if not port then return end
    local port_num = tonumber(port)
    -- 下界按需收紧，避免把内部端口暴露到公网（同目录 `nginx-multiport-routes.conf` 放行 1024 以上）
    if not port_num or port_num < 1024 or port_num > 65535 then return end
    ngx.var.target_port = port
    ngx.exec("@multiport")
}

location @multiport {
    # 必须覆盖继承来的 server 级 rewrite_by_lua_block，
    # 否则内部重定向进来后又 ngx.exec 一次 → 重定向死循环
    rewrite_by_lua_block { return }

    proxy_pass http://127.0.0.1:$target_port;
    proxy_set_header Host localhost:$target_port;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_connect_timeout 7d;
    proxy_send_timeout 7d;
    proxy_read_timeout 7d;

    # envd 用 connect 协议，需要 HTTP/1.1 且关闭缓冲
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_buffering off;
    proxy_request_buffering off;
}
```

把它加进 Dockerfile 时，同样带上构建期自检（openresty 的路径，且 `-t` 要带 prefix）：

```dockerfile
COPY nginx-multiport-http.conf   /etc/openresty/http.d/00-multiport.conf
COPY nginx-multiport-routes.conf /etc/openresty/conf.d/00-multiport-routes.conf
RUN /usr/local/openresty/bin/openresty -p /var/lib/openresty -c /etc/openresty/nginx.conf -t; \
    grep -qE '^\s*listen 0\.0\.0\.0:5000;' /etc/openresty/nginx.conf; \
    grep -q 'rewrite_by_lua_no_postpone on;' /etc/openresty/http.d/00-multiport.conf; \
    grep -q 'ngx.exec("@multiport")' /etc/openresty/conf.d/00-multiport-routes.conf
```

`openresty -t` 只管语法，那三条 `grep` 才管语义：配置能解析但 `listen` 写成 `127.0.0.1:5000`、
或者少了 `rewrite_by_lua_no_postpone`，`-t` 一样是 `successful`，要到沙箱里才炸。

> 实测（`verify-local.sh` 第 ③ 项）：业务侧故意留了
> `location = /health { return 200 … }` 这个抢答陷阱，带 `X-Sandbox-Port: 49983` 打 `/health`
> 拿到的是 204（envd 的）而不是 200（业务的），这就是
> `rewrite_by_lua_no_postpone on;` 在起作用。同一个请求不带端口信息时仍是业务的 200，
> 两边互不影响。

## 3. SDK 默认用户 `user`：自定义镜像必须自己建

这是「监听 5000 / 多端口路由 / envd 常驻」三个必要条件之外的第 ④ 个，只有从零搭的镜像会踩。

e2b SDK 的 `default_username` 是 `"user"`（`e2b/connection_config.py`）：你不指定 `user=`
时，每一条 `commands.run` 都会让 envd 去 `/etc/passwd` 查 `user` 这个账号并降权执行。

失败形态很有辨识度（实测，用 `commands.run(..., user="nosuchuser")` 复现）：

```
AuthenticationException: 用户 nosuchuser 不存在: user: unknown user nosuchuser
```

注意这时沙箱创建成功、envd 也在跑、`/health` 也是 204，三个必要条件全绿，
但 SDK 一条命令都跑不了，所以它值得单列一条。对齐 runtime base 镜像建账号：

```dockerfile
RUN set -eux; \
    groupadd --gid 1000 user; \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash user; \
    chown user:user /home/user
WORKDIR /home/user
```

构建期护栏 + 运行期验证各一条：

```dockerfile
RUN id user; [ "$(id -u user)" = "1000" ]; getent passwd user | grep -q ':/home/user:/bin/bash$'
```

```python
assert sbx.commands.run("whoami").stdout.strip() == "user"
```

> `files` 和 `commands` 走 envd 的不同接口，前者通不代表后者通，反之亦然。
> 所以 `run.py` 在 `whoami` 之外还做了一次 `files.write` / `files.read` 往返
> （写 `/home/user/…`，顺带验证家目录属主对不对）。

## 4. 从零搭镜像的四个坑

这四个坑都是实际撞上的，共同点是构建能过、表面正常，要到运行期才炸：

| 坑 | 表现 | 处置 |
|---|---|---|
| `deb.debian.org` 在国内不可用 | `apt-get install` 挂十几分钟不报错（Release 探测 1.7s 就回，但 pool 目录列不出来） | `ARG DEBIAN_MIRROR=http://mirrors.aliyun.com` + sed 换源，实测 9MB/s |
| `python3-minimal` 缺标准库 | 业务进程 `ModuleNotFoundError: No module named 'http'`，被 supervisord 无限重启，表现为业务端口一直 **502** | 用 `python3`；构建期加 `python3 -c 'import http.server, socketserver, json'` |
| debian-slim 里没有 `ss` / `netstat` | 本地验证脚本（同目录 `verify-local.sh`）里的 `ss -ltn` 直接不存在，静默漏判 | 装 `iproute2`；构建期加 `command -v ss` |
| 换源用了 `sources.list` | bookworm slim 是 **deb822** 格式，改的文件根本不生效 | 改 `/etc/apt/sources.list.d/debian.sources`，并断言 `! grep -q 'deb.debian.org'` |

共同的教训：凡是「构建能过、运行期才炸」的东西，都往 `RUN` 里塞一条断言。
Dockerfile 末尾那一串 `command -v` / `import` / `envd -version` / `id user` /
`openresty -t` / `grep` / configparser 断言就是这么长出来的，每一条都曾经真的失败过一次。

## 5. 移植检查表

| 项 | 官方 `sandbox-*` 镜像 | 你自己的镜像（本文实测） |
|---|---|---|
| envd 二进制 | `COPY --from=base:v0.0.44 /.fce2b/envd` | 同左（静态链接，跨发行版可用） |
| envd 常驻 | 加 `process-compose.envd.yaml` + 注册 | supervisord 托管 + `startretries` 调大（见 [1](#1-没有-process-compose用-supervisord-托管-envd)） |
| 5000 监听 | 通常已有 | 自己装 openresty（见 [2](#2-没有-5000-上的多端口反代加一层-openresty)） |
| 多端口路由 | 通常已有 | 自己写（见 [2](#2-没有-5000-上的多端口反代加一层-openresty)） |
| `user` 账号 | 自带 | **必须自己建**（见 [3](#3-sdk-默认用户-user自定义镜像必须自己建)） |
| 构建期自检 | 与 vendor 原文件精确 diff + `bash -n` + `nginx -t` | `openresty -t` + 语义 `grep` + `id user` + 依赖 `import`（见 [4](#4-从零搭镜像的四个坑)） |

---

## 附录：文件清单

源码就在本目录（`e2b-custom-image/`），逐个文件的设计取舍见上文 §1–4。这一整套已完整跑通 build → 本地验证 → push → 模板构建 → 创建沙箱 → `commands.run` / `files` 可用。各文件用途一览：

```
e2b-custom-image/
├── Dockerfile                    # debian-slim + openresty + supervisor + envd + user 账号
├── nginx.conf                    # ① listen 0.0.0.0:5000
├── nginx-multiport-http.conf     # ② http 级：map + rewrite_by_lua_no_postpone
├── nginx-multiport-routes.conf   # ② server 级：多端口路由
├── nginx-app-routes.conf         # 业务路由（含 location = /health，故意留的抢答陷阱）
├── supervisord.conf              # ③ 主配置：nodaemon + socket + include conf.d
├── supervisor-envd.conf          # ③ envd —— 可整份搬到你自己镜像的那一份
├── supervisor-openresty.conf     # 反代（daemon off + stopsignal=QUIT）
├── supervisor-app.conf           # 示例业务进程
├── entrypoint.sh                 # 只做目录准备 + exec supervisord
├── app.py                        # 示例业务进程（127.0.0.1:8000）
├── verify-local.sh               # 步骤 3 的本地验证，7 项断言
├── build.py                      # docker build → push → 模板构建
├── run.py                        # 创建沙箱并验证 envd / supervisord 状态 / user / files
├── requirements.txt              # e2b SDK + python-dotenv
└── env.example                   # E2B_API_KEY / _API_URL / _DOMAIN 等，复制成 .env
```
