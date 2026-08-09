""" 自定义 debian 镜像 + envd：拉起 sandbox 并校验 envd 已运行。

这里多验两件只有自定义镜像才会踩的事：
  - `user` 账号：SDK 的 default_username 是 "user"，没有这个账号 commands.run 全挂
  - files API：commands.run 和 files 走 envd 的不同接口，前者通不代表后者通
"""

import os
import sys
import time

from dotenv import load_dotenv
from e2b import Sandbox

load_dotenv()

# SDK 自动从环境变量读取 E2B_API_KEY / E2B_API_URL / E2B_DOMAIN（见根目录 README、env.example）。
REQUIRED_ENV = ("E2B_API_KEY", "E2B_API_URL", "E2B_DOMAIN")

TEMPLATE_NAME = os.environ.get("E2B_TEMPLATE_NAME", "envd-custom-debian-4c8g-v2")
SANDBOX_TIMEOUT_SECONDS = int(os.environ.get("E2B_TIMEOUT", "900"))
ENVD_PORT = 49983
# 与 nginx-app-routes.conf 的 proxy_pass 是同一个约定端口，改一处要同时改另一处。
APP_PORT = 8000


def require_env() -> None:
    """缺少任一 E2B 环境变量就直接退出，不把空值传给 SDK。"""
    missing = [name for name in REQUIRED_ENV if not os.getenv(name)]
    if missing:
        sys.exit("缺少环境变量：" + ", ".join(missing) + "（见根目录 README、env.example）")

# 探活命令：不止看退出码，还要看 stdout 是否原样回传 ——
# envd 能 fork 进程但输出流坏掉时，`true` 这类无输出的命令照样会过
PROBE_COMMAND = "echo envd-ok"
PROBE_EXPECTED = "envd-ok"

# Sandbox.create 返回后 envd 可能还没被网关路由到（镜像越大冷启越慢），首个命令要重试
CONNECT_RETRIES = 12
CONNECT_RETRY_INTERVAL_SECONDS = 15

# 沙箱内的就绪检查：envd 进程 / 端口 / health，外加 openresty 和业务进程
CHECK_SH = f"""
set -u
rc=0

echo "--- processes:"
ps -ef | grep -v grep | grep -E "supervisord|bin/envd|nginx: master|app.py" || true

# 即时快照，可能是 STARTING（startsecs 未满）；下面的轮询才是判据
echo "--- supervisorctl status (即时快照):"
supervisorctl status || true

# 三个进程都必须 RUNNING。FATAL 要单独抓：那是「重试耗尽、再也不拉起」的终态，
# 光看端口在不在听会漏判（进 FATAL 之前 supervisord 已经重启过几次）。
#
# 必须轮询而不是采样一次：startsecs=1 未满时状态是 STARTING，沙箱恢复得很快，
# 首个命令经常就落在这 1 秒内 —— 采样一次会把 STARTING 误判成失败。
# BACKOFF 同理是过渡态（会走向 RUNNING 或 FATAL），只有 RUNNING/FATAL/EXITED 是终态。
for prog in envd openresty my-app; do
    state=""
    for _ in 1 2 3 4 5 6 7 8 9 10; do
        state=$(supervisorctl status "$prog" 2>/dev/null | awk '{{print $2}}')
        case "$state" in RUNNING|FATAL|EXITED) break ;; esac
        sleep 2
    done
    if [ "$state" = "RUNNING" ]; then
        echo "OK   supervisord: $prog RUNNING"
    else
        echo "FAIL supervisord: $prog -> ${{state:-unknown}}"
        rc=1
    fi
done

if ps -ef | grep -v grep | grep -q "/usr/local/bin/envd"; then
    echo "OK   envd process running"
else
    echo "FAIL envd process not found"
    rc=1
fi

if nc -z localhost {ENVD_PORT}; then
    echo "OK   port {ENVD_PORT} listening"
else
    echo "FAIL port {ENVD_PORT} not listening"
    rc=1
fi

if nc -z localhost 5000; then
    echo "OK   port 5000 listening (openresty)"
else
    echo "FAIL port 5000 not listening"
    rc=1
fi

code=$(curl -s -o /dev/null -w "%{{http_code}}" -m 5 http://localhost:{ENVD_PORT}/health || echo 000)
if [ "$code" = "200" ] || [ "$code" = "204" ]; then
    echo "OK   envd /health -> $code"
else
    echo "FAIL envd /health -> $code"
    rc=1
fi

code=$(curl -s -o /dev/null -w "%{{http_code}}" -m 5 http://localhost:{APP_PORT}/ || echo 000)
if [ "$code" = "200" ]; then
    echo "OK   业务进程 :{APP_PORT} -> 200"
else
    echo "FAIL 业务进程 :{APP_PORT} -> $code"
    rc=1
fi

exit $rc
"""


def wait_for_envd(sbx: Sandbox) -> bool:
    """等 envd 可以接命令。commands.run 本身就走 envd，能跑通即证明 envd 已在服务。"""
    for attempt in range(1, CONNECT_RETRIES + 1):
        try:
            stdout = sbx.commands.run(PROBE_COMMAND).stdout.strip()
            if stdout != PROBE_EXPECTED:
                raise RuntimeError(f"stdout 回传异常，期望 {PROBE_EXPECTED!r} 得到 {stdout!r}")
            print(f"OK   envd reachable, stdout 回传正常 (attempt {attempt})")
            return True
        except Exception as exc:
            print(f"...  waiting for envd (attempt {attempt}/{CONNECT_RETRIES}): {type(exc).__name__}")
            if attempt < CONNECT_RETRIES:
                time.sleep(CONNECT_RETRY_INTERVAL_SECONDS)
            else:
                print(f"FAIL envd unreachable: {str(exc)[:200]}")
    return False


def check_envd(sbx: Sandbox) -> bool:
    # 用 root 跑：supervisord 的控制 socket 是 chmod=0700 root 独占的，
    # 默认的 `user` 身份读不到（这是故意的 —— 否则沙箱里的用户能 stop 掉 root 起的 envd）。
    # 「默认身份可用」由 check_default_user / check_files_api 单独验证。
    try:
        result = sbx.commands.run(CHECK_SH, user="root")
        print(result.stdout)
        return True
    except Exception as exc:  # 退出码非 0 时 SDK 抛异常
        # 异常的 str() 只有 exit code 和 stderr，逐项 OK/FAIL 都在 stdout 里 ——
        # 不显式打出来的话，看到的就只是一句「exited with code 1」，等于没有信息
        print("envd check failed:")
        print(getattr(exc, "stdout", "") or "<no stdout>")
        print(exc)
        return False


def check_default_user(sbx: Sandbox) -> bool:
    """SDK 不指定 user 时以 `user` 身份执行，自定义镜像必须自己建这个账号。"""
    try:
        who = sbx.commands.run("whoami").stdout.strip()
        if who == "user":
            print("OK   默认执行身份是 user（SDK default_username）")
            return True
        print(f"FAIL 默认执行身份是 {who!r}，不是 user（SDK default_username）")
        return False
    except Exception as exc:
        print(f"FAIL whoami 失败，`user` 账号可能不存在: {str(exc)[:200]}")
        return False


def check_files_api(sbx: Sandbox) -> bool:
    """files 和 commands 走 envd 的不同接口，前者通不代表后者通。"""
    path = "/home/user/-envd-check.txt"
    payload = "hello-from-"
    try:
        sbx.files.write(path, payload)
        got = sbx.files.read(path)
        if got.strip() != payload:
            print(f"FAIL files 往返内容不一致：{got!r}")
            return False
        print("OK   files.write / files.read 往返正常")
        return True
    except Exception as exc:
        print(f"FAIL files API 失败: {str(exc)[:200]}")
        return False


def main() -> int:
    require_env()
    sbx = Sandbox.create(template=TEMPLATE_NAME, timeout=SANDBOX_TIMEOUT_SECONDS)
    try:
        print(f"sandbox_id: {sbx.sandbox_id}")

        if not wait_for_envd(sbx):
            print("RESULT: FAIL - envd unreachable")
            return 1

        checks = [
            check_envd(sbx),
            check_default_user(sbx),
            check_files_api(sbx),
        ]
        if all(checks):
            print("RESULT: PASS - envd is running in the custom debian sandbox")
            return 0
        print("RESULT: FAIL - some checks failed")
        return 1
    finally:
        sbx.kill()


if __name__ == "__main__":
    sys.exit(main())
