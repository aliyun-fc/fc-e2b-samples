# 完整的自定义镜像 —— 从 debian:bookworm-slim 从零搭出一个可用的 e2b 沙箱模板。
#
# 这里什么都没有，三个必要条件全部要自己补：
#   ① 有进程监听 0.0.0.0:5000        → 自己装 openresty（见 nginx.conf）
#   ② nginx 按 Host 端口前缀转发     → 自己写 multiport 配置（见 nginx-multiport-*.conf）
#   ③ envd 常驻并监听 49983          → supervisord 托管（见 supervisor-envd.conf）
# 外加一条只有自定义镜像才会踩的：SDK 默认以 `user` 身份执行命令，这个账号也得自己建。

# Stage 1: 从 runtime base 镜像中提取 envd 二进制（静态链接，可直接放进任何发行版）
FROM fc-e2b-registry.cn-hangzhou.cr.aliyuncs.com/runtime/base:v0.0.44 AS envd-extract

# Stage 2: 目标镜像
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    ENVD_PORT=49983

# apt 镜像站。默认走 mirrors.aliyun.com：在国内（尤其阿里云机器上）拉包约 9MB/s，
# 而 deb.debian.org 实测连 pool 目录都列不出来，会让 apt-get install 挂十几分钟。
# 想用官方源：docker build --build-arg DEBIAN_MIRROR=http://deb.debian.org …
ARG DEBIAN_MIRROR=http://mirrors.aliyun.com

# bookworm 的 slim 镜像用 deb822 格式（/etc/apt/sources.list.d/debian.sources），
# 只替换主机名，debian 和 debian-security 两个 URI 一起改掉。
RUN sed -i "s|http://deb.debian.org|${DEBIAN_MIRROR}|g" /etc/apt/sources.list.d/debian.sources \
    && ! grep -q 'deb.debian.org' /etc/apt/sources.list.d/debian.sources

# openresty 官方 apt 源（需要 openresty 而不是 nginx：多端口路由用到 lua）。
# 顺带装上验证/运行期要用的工具，每一个都是踩过的坑：
#   curl + netcat-openbsd → 本地和沙箱内的探活（教程步骤 3 / run.py 都要用）
#   iproute2             → ss -ltn 看 5000/49983 在不在听；debian-slim 里 ss 和 netstat 都没有
#   procps               → ps -ef 看 envd 在不在
#   supervisor           → 进程管理器，托管 envd / openresty / 业务进程
#   python3              → 示例业务进程（supervisor 也依赖它）。**不能用 python3-minimal**：
#                          它不含 http.server 依赖的那部分标准库，app.py 会
#                          ModuleNotFoundError: No module named 'http'，
#                          然后被 supervisord 无限重启，表现为业务端口一直 502。
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg; \
    curl -fsSL https://openresty.org/package/pubkey.gpg \
        | gpg --dearmor -o /usr/share/keyrings/openresty.gpg; \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/openresty.gpg] \
http://openresty.org/package/debian bookworm openresty" \
        > /etc/apt/sources.list.d/openresty.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        openresty \
        supervisor \
        netcat-openbsd \
        iproute2 \
        procps \
        python3; \
    apt-get purge -y --auto-remove gnupg; \
    rm -rf /var/lib/apt/lists/*

# ─── ③ envd 二进制 ───────────────────────────────────────────────────────────
COPY --from=envd-extract /.fce2b/envd /usr/local/bin/envd

# ─── SDK 默认用户 ───────────────────────────────────────────────────────────
# e2b SDK 的 default_username 是 "user"（connection_config.py），envd 会按这个名字
# 查 /etc/passwd 并降权执行命令。自定义镜像里没有这个账号，沙箱能创建、envd 也在跑，
# 但每一条 commands.run 都会失败
# 这里对齐 runtime base 镜像：uid/gid 1000、家目录 /home/user、shell /bin/bash。
RUN set -eux; \
    groupadd --gid 1000 user; \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash user; \
    chown user:user /home/user

# ─── ① ② openresty 配置 ─────────────────────────────────────────────────────
COPY nginx.conf                  /etc/openresty/nginx.conf
COPY nginx-multiport-http.conf   /etc/openresty/http.d/00-multiport.conf
COPY nginx-multiport-routes.conf /etc/openresty/conf.d/00-multiport-routes.conf
COPY nginx-app-routes.conf       /etc/openresty/conf.d/10-app-routes.conf

RUN mkdir -p \
        /var/lib/openresty/client_body_temp \
        /var/lib/openresty/proxy_temp \
        /var/lib/openresty/fastcgi_temp \
        /var/lib/openresty/uwsgi_temp \
        /var/lib/openresty/scgi_temp \
        /var/lib/openresty/logs \
        /var/log/supervisor

# ─── 示例业务进程 ───────────────────────────────────────────────────────────
COPY app.py /usr/local/lib/myapp/app.py

# ─── 进程托管：supervisord ──────────────────────────────────────────────────
# 一个进程一个文件。10-envd.conf 是可以整份搬到你自己镜像里的那一份：
# 镜像已经在用 supervisord 的话，集成 envd 就只有这一个 COPY。
COPY supervisord.conf           /etc/supervisor/supervisord.conf
COPY supervisor-envd.conf       /etc/supervisor/conf.d/10-envd.conf
COPY supervisor-openresty.conf  /etc/supervisor/conf.d/20-openresty.conf
COPY supervisor-app.conf        /etc/supervisor/conf.d/30-my-app.conf

# ─── entrypoint ─────────────────────────────────────────────────────────────
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# ─── 构建期护栏 ─────────────────────────────────────────────────────────────
# 每一条都对应一个「构建能过、运行期才炸」的失败模式，宁可在这里 build 失败。
RUN set -eux; \
    chmod 0755 /usr/local/bin/entrypoint.sh /usr/local/bin/envd; \
    bash -n /usr/local/bin/entrypoint.sh; \
    python3 -c 'import py_compile; py_compile.compile("/usr/local/lib/myapp/app.py", doraise=True)'; \
    python3 -c 'import http.server, socketserver, json'; \
    command -v ss; \
    command -v nc; \
    command -v ps; \
    command -v supervisord; \
    command -v supervisorctl; \
    /usr/local/bin/envd -version; \
    id user; \
    [ "$(id -u user)" = "1000" ]; \
    getent passwd user | grep -q ':/home/user:/bin/bash$'; \
    /usr/local/openresty/bin/openresty -p /var/lib/openresty -c /etc/openresty/nginx.conf -t; \
    grep -qE '^\s*listen 0\.0\.0\.0:5000;' /etc/openresty/nginx.conf; \
    grep -q 'rewrite_by_lua_no_postpone on;' /etc/openresty/http.d/00-multiport.conf; \
    grep -q 'ngx.exec("@multiport")' /etc/openresty/conf.d/00-multiport-routes.conf; \
    [ "$(ls /etc/supervisor/conf.d/*.conf | wc -l)" = "3" ]

# supervisord 配置的语义护栏。它没有 `-t` 这样的 dry-run，所以用 configparser 按
# supervisord 自己的解析规则（不剥行尾注释）读一遍，断言关键值就是字面上那几个：
#   - nodaemon=true          少了它 PID 1 秒退，容器直接结束
#   - envd autorestart=true  少了它 envd 崩了不再拉起，沙箱静默失能
#   - startretries 足够大    默认的 3 会让 envd 快速失败 3 次后进 FATAL 永不再起
# 顺带挡住「写了行尾 `; 注释` 导致值变成 'true ; 注释'」这个 supervisord 特有的坑。
RUN set -eux; \
    python3 -c "import configparser, glob; \
cp = configparser.ConfigParser(interpolation=None); \
cp.read(['/etc/supervisor/supervisord.conf'] + sorted(glob.glob('/etc/supervisor/conf.d/*.conf'))); \
assert cp.get('supervisord', 'nodaemon') == 'true'; \
assert cp.get('include', 'files') == '/etc/supervisor/conf.d/*.conf'; \
assert cp.get('program:envd', 'command') == '/usr/local/bin/envd'; \
assert all(cp.get('program:' + p, 'autorestart') == 'true' for p in ('envd', 'openresty', 'my-app')); \
assert int(cp.get('program:envd', 'startretries')) >= 1000000"

EXPOSE 5000 8000 49983

WORKDIR /home/user

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
