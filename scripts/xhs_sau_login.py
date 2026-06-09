"""
薯光笔记 -> social-auto-upload 小红书登录适配器。

后端会把 payload.json 路径作为最后一个参数传入；这里读取账号名称，
再调用 sau 的真实登录命令。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "缺少 payload.json 路径"}, ensure_ascii=False))
        return 2

    payload_path = Path(sys.argv[-1])
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    account = payload.get("account", {}).get("name")
    if not account:
        print(json.dumps({"success": False, "error": "payload 中缺少账号名称"}, ensure_ascii=False))
        return 2

    sau_bin = os.environ.get("SAU_BIN", "sau")
    profile_dir = Path(payload.get("account", {}).get("profile_dir") or ".").resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = env.get("PLAYWRIGHT_BROWSERS_PATH", "0")
    env["CHROME_USER_DATA_DIR"] = str(profile_dir)
    env["SAU_COOKIE_DIR"] = str(profile_dir)
    command = [sau_bin, "xiaohongshu", "login", "--account", account, "--headed"]
    completed = subprocess.run(command, env=env)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
