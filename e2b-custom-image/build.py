""" 自定义 debian 镜像 + envd：docker build/push + e2b 模板构建。

推送用公网地址；模板构建用 VPC 地址。

注意两个平台侧限制，重跑本脚本前要换名字：
  1. ACR 的 tag 不可覆盖，push 已存在的 tag 会报 "tag is already existed"
  2. 一个模板名只允许构建一次，重复 build 会报 409 "only a single build"
"""

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from e2b import Template, default_build_logger

load_dotenv()


def required_env(name: str) -> str:
    """读取必填环境变量，不把空值传给 SDK；缺失直接退出。"""
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"缺少环境变量 {name}（见根目录 README、env.example）")
    return value


# 镜像地址：两项都必填，没有默认值——回退到别人的私有仓库外部用户必然推不上去，
# 只设一项还可能 push 和 build 用的不是同一个镜像。IMAGE 走公网供 docker push，
# FROM_IMAGE 走 VPC 供 e2b 构建服务拉取，地域要和 E2B_API_URL 一致。
IMAGE = required_env("E2B_IMAGE")
FROM_IMAGE = required_env("E2B_FROM_IMAGE")

TEMPLATE_NAME = os.environ.get("E2B_TEMPLATE_NAME", "envd-custom-debian-4c8g-v2")
CPU_COUNT = int(os.environ.get("E2B_TEMPLATE_CPU", "4"))
MEMORY_MB = int(os.environ.get("E2B_TEMPLATE_MEMORY_MB", "8192"))

HERE = Path(__file__).parent


def run(cmd: list[str]) -> None:
    """执行命令，失败直接退出（不吞错）。"""
    print(f"\n$ {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, cwd=HERE)
    if result.returncode != 0:
        sys.exit(f"command failed with exit code {result.returncode}: {' '.join(cmd)}")


def docker_build_push() -> None:
    run(["docker", "build", "--platform", "linux/amd64", "-t", IMAGE, "."])
    run(["docker", "push", IMAGE])


def template_build() -> None:
    build = Template.build(
        Template().from_image(FROM_IMAGE),
        name=TEMPLATE_NAME,
        cpu_count=CPU_COUNT,
        memory_mb=MEMORY_MB,
        # 后端不支持 force：skip_cache=True 会报 400 force is not supported
        skip_cache=False,
        on_build_logs=default_build_logger(),
        headers={"X-E2B-Template-Build-Mode": "direct"},
        api_key=required_env("E2B_API_KEY"),
        api_url=required_env("E2B_API_URL"),
        domain=required_env("E2B_DOMAIN"),
    )
    print(f"template_name: {TEMPLATE_NAME}")
    print(f"template_id: {build.template_id}")
    print(f"build_id: {build.build_id}")


if __name__ == "__main__":
    # 先校验凭据再动手，别等 docker build/push 跑完才在模板构建这步报缺环境变量。
    for _name in ("E2B_API_KEY", "E2B_API_URL", "E2B_DOMAIN"):
        required_env(_name)
    docker_build_push()
    template_build()
