#!/bin/bash
# entrypoint：只做 supervisord 起不动的准备工作，然后 exec supervisord。
#
# 进程托管全部声明式地放在 /etc/supervisor/conf.d/ 里（envd / openresty / 业务进程），
# 这个脚本里没有任何进程管理逻辑，对应教程第 1 节「用 supervisord 托管 envd」。
set -euo pipefail

OPENRESTY_PREFIX=${OPENRESTY_PREFIX:-/var/lib/openresty}
SUPERVISORD_BIN=${SUPERVISORD_BIN:-/usr/bin/supervisord}
SUPERVISORD_CONF=${SUPERVISORD_CONF:-/etc/supervisor/supervisord.conf}

log() { echo "[entrypoint] $*" >&2; }

# 这些目录构建期已经建好，这里兜住被 volume 挂空 / tmpfs 覆盖的情况
mkdir -p \
    "${OPENRESTY_PREFIX}/client_body_temp" \
    "${OPENRESTY_PREFIX}/proxy_temp" \
    "${OPENRESTY_PREFIX}/fastcgi_temp" \
    "${OPENRESTY_PREFIX}/uwsgi_temp" \
    "${OPENRESTY_PREFIX}/scgi_temp" \
    "${OPENRESTY_PREFIX}/logs" \
    /var/log/supervisor

# exec：supervisord 取代本脚本成为 PID 1，负责信号转发、僵尸回收和崩溃重启。
# 用 exec 而不是后台起 + wait，否则容器收到 TERM 时信号到不了 supervisord。
log "exec supervisord: envd:${ENVD_PORT:-49983} / openresty:5000 / my-app:${APP_PORT:-8000}"
exec "${SUPERVISORD_BIN}" -c "${SUPERVISORD_CONF}" -n
