#!/bin/bash
# 本地验证：对应教程「步骤 3：本地验证（最便宜的一轮）」。
#
# push 和模板构建都慢，先在本地把能验的全验完。
# -p 15000:5000 的左边是宿主机端口、右边是容器内端口：容器里 openresty 只听 5000
# （网关也只认 5000），宿主机映射到 15000 只是避免和本机已占用的 5000 冲突。
#
# 用法：./verify-local.sh [image]
set -uo pipefail

IMAGE=${1:-envd-custom-debian:local}
NAME=envd-verify
HOST_PORT=15000
ENVD_PORT=49983
APP_PORT=8000

rc=0
pass() { echo "OK   $*"; }
fail() { echo "FAIL $*"; rc=1; }

cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

cleanup
echo "--- starting $IMAGE (4C8G, 与模板规格一致)"
docker run -d --name "$NAME" --cpus 4 --memory 8g -p "${HOST_PORT}:5000" "$IMAGE" >/dev/null \
    || { echo "FAIL docker run"; exit 1; }

# openresty + envd + 业务进程都要起来；envd 是静态 Go 二进制，起得很快
for _ in $(seq 30); do
    docker exec "$NAME" sh -c "nc -z localhost ${ENVD_PORT} && nc -z localhost 5000" >/dev/null 2>&1 && break
    sleep 1
done

echo
echo "=== ① 进程与监听端口 ==="
docker exec "$NAME" ps -ef | grep -vE 'grep|ps -ef' | grep -E 'supervisord|openresty|nginx|envd|app.py' || true
echo
docker exec "$NAME" ss -ltn 2>/dev/null || docker exec "$NAME" netstat -ltn 2>/dev/null || true
echo
# supervisorctl 是排错第一现场：谁没起来、重启过几次，一眼可见
docker exec "$NAME" supervisorctl status || true

# 等某个 program 走到终态。STARTING（startsecs 未满）和 BACKOFF 都是过渡态，
# 采样一次会误判；只有 RUNNING / FATAL / EXITED 才是结论。
wait_state() {
    local prog=$1 state=""
    for _ in $(seq 10); do
        state=$(docker exec "$NAME" supervisorctl status "$prog" 2>/dev/null | awk '{print $2}')
        case "$state" in RUNNING|FATAL|EXITED) break ;; esac
        sleep 2
    done
    echo "$state"
}

# 三个进程都必须是 RUNNING。FATAL 尤其要抓：那是「重试耗尽、再也不拉起」的终态
for prog in envd openresty my-app; do
    state=$(wait_state "$prog")
    [ "$state" = "RUNNING" ] && pass "supervisord: $prog RUNNING" \
                             || fail "supervisord: $prog 状态是 ${state:-<未知>}（期望 RUNNING）"
done

for spec in "0.0.0.0:5000|5000(openresty)" "${ENVD_PORT}|${ENVD_PORT}(envd)" "${APP_PORT}|${APP_PORT}(业务)"; do
    port=${spec%%|*}; label=${spec##*|}
    if docker exec "$NAME" sh -c "ss -ltn 2>/dev/null | grep -q '${port}'"; then
        pass "listening ${label}"
    else
        fail "not listening ${label}"
    fi
done

if docker exec "$NAME" sh -c "ps -ef | grep -v grep | grep -q '/usr/local/bin/envd'"; then
    pass "envd 进程在跑"
else
    fail "envd 进程不在"
fi

echo
echo "=== ② 沙箱内直连 envd（期望 204）==="
code=$(docker exec "$NAME" curl -s -o /dev/null -w '%{http_code}' -m 5 "http://localhost:${ENVD_PORT}/health")
[ "$code" = "204" ] && pass "envd /health -> 204" || fail "envd /health -> $code（期望 204）"

echo
echo "=== ③ 模拟网关：带端口信息打到 5000，看能不能转到 envd（最关键的一条）==="
# X-Sandbox-Port 头
code=$(curl -s -o /dev/null -w '%{http_code}' -m 5 -H "X-Sandbox-Port: ${ENVD_PORT}" "http://127.0.0.1:${HOST_PORT}/health")
[ "$code" = "204" ] && pass "X-Sandbox-Port: ${ENVD_PORT} + /health -> 204（envd 赢过业务的 200）" \
                    || fail "X-Sandbox-Port: ${ENVD_PORT} + /health -> $code（期望 204）"

# Host 端口前缀，网关真实用法
code=$(curl -s -o /dev/null -w '%{http_code}' -m 5 \
       -H "Host: ${ENVD_PORT}-x.us-west-1.e2b.fc.aliyuncs.com" "http://127.0.0.1:${HOST_PORT}/health")
[ "$code" = "204" ] && pass "Host: ${ENVD_PORT}-x.<domain> + /health -> 204" \
                    || fail "Host: ${ENVD_PORT}-x.<domain> + /health -> $code（期望 204）"

# 未定义路径：期望 envd 自己的纯文本 404，而不是 openresty 的 404 HTML
body=$(curl -s -m 5 -H "X-Sandbox-Port: ${ENVD_PORT}" "http://127.0.0.1:${HOST_PORT}/__nope")
case "$body" in
    *"404 page not found"*) pass "/__nope -> envd 的纯文本 404（整条链路通）" ;;
    *) fail "/__nope -> 不是 envd 的 404，实际：$(echo "$body" | head -c 120)" ;;
esac

echo
echo "=== ④ 业务端口也能通过端口前缀访问 ==="
body=$(curl -s -m 5 -H "X-Sandbox-Port: ${APP_PORT}" "http://127.0.0.1:${HOST_PORT}/api/hello")
case "$body" in
    *'"service": "my-app"'*) pass "X-Sandbox-Port: ${APP_PORT} -> 业务进程" ;;
    *) fail "X-Sandbox-Port: ${APP_PORT} -> 未到业务进程，实际：$(echo "$body" | head -c 120)" ;;
esac

echo
echo "=== ⑤ 不带端口信息时业务路由不受影响 ==="
body=$(curl -s -m 5 "http://127.0.0.1:${HOST_PORT}/health")
case "$body" in
    *my-app-nginx*) pass "/health -> 业务自己的 200（nginx location = /health）" ;;
    *) fail "/health -> 业务路由被破坏，实际：$(echo "$body" | head -c 120)" ;;
esac

body=$(curl -s -m 5 "http://127.0.0.1:${HOST_PORT}/api/hello")
case "$body" in
    *'"service": "my-app"'*) pass "/api/hello -> 业务进程" ;;
    *) fail "/api/hello -> 未到业务进程，实际：$(echo "$body" | head -c 120)" ;;
esac

echo
echo "=== ⑥ SDK 默认用户 user 存在且可用 ==="
if docker exec "$NAME" id user >/dev/null 2>&1; then
    who=$(docker exec "$NAME" su - user -c whoami 2>/dev/null | tr -d '\r')
    [ "$who" = "user" ] && pass "user 账号存在且可登录（envd 按此身份执行 commands.run）" \
                        || fail "user 账号存在但 su 失败：$who"
else
    fail "user 账号不存在 —— commands.run 会全部失败"
fi

echo
echo "=== ⑦ envd 崩溃后自动拉起（supervisord autorestart）==="
docker exec "$NAME" pkill -9 -f '/usr/local/bin/envd' >/dev/null 2>&1 || true
sleep 6
if docker exec "$NAME" sh -c "nc -z localhost ${ENVD_PORT}"; then
    pass "kill -9 后 envd 已被自动拉起"
else
    fail "kill -9 后 envd 没有恢复 —— autorestart 失效"
fi
# 只看端口恢复不够：进 FATAL 前 supervisord 也会重启几次，端口可能刚好是那几次之一
state=$(wait_state envd)
[ "$state" = "RUNNING" ] && pass "envd 重启后状态回到 RUNNING（不是 FATAL/BACKOFF）" \
                         || fail "envd 重启后状态是 ${state:-<未知>}"

echo
[ "$rc" = "0" ] && echo "RESULT: PASS - 本地三个必要条件全部满足" || echo "RESULT: FAIL"
exit "$rc"
