"""
薯光笔记 -> social-auto-upload 小红书 CLI 适配器。

用法由 backend/services/publish.py 自动调用：
    python scripts/xhs_sau_wrapper.py payload.json

要求：
    1. 已安装 social-auto-upload，并且终端里可以运行 sau
    2. 已用相同 account 名称完成 sau xiaohongshu login

注意：
    social-auto-upload 的 upload-note 会点击最终发布按钮。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


TRUE_VALUES = {"1", "true", "yes", "on"}


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "缺少 payload.json 路径"}, ensure_ascii=False))
        return 2

    payload_path = Path(sys.argv[-1])
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    account = payload["account"]["name"]
    post = payload["post"]
    title = post["title"]
    tags = [str(tag).lstrip("#") for tag in post.get("tags", [])]
    note = post["body"].strip()
    images = []
    seen_images = set()
    for item in post.get("media", []):
        image_path = item["path"]
        if image_path in seen_images:
            continue
        seen_images.add(image_path)
        images.append(image_path)

    if not images:
        print(json.dumps({"success": False, "error": "payload 中没有图片"}, ensure_ascii=False))
        return 2

    sau_bin = os.environ.get("SAU_BIN", "sau")
    profile_dir = Path(payload.get("account", {}).get("profile_dir") or ".").resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sau_bin,
        "xiaohongshu",
        "upload-note",
        "--account",
        account,
        "--images",
        *images,
        "--title",
        title,
        "--note",
        note,
        "--headed",
    ]
    if tags:
        command.extend(["--tags", ",".join(tags)])

    click_publish = bool(post.get("click_publish"))
    allow_direct_publish = (
        os.environ.get("SHUGUANG_NOTE_ALLOW_DIRECT_PUBLISH")
        or os.environ.get("REDINK_ALLOW_DIRECT_PUBLISH", "")
    ).lower() in TRUE_VALUES
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = env.get("PLAYWRIGHT_BROWSERS_PATH", "0")
    env["CHROME_USER_DATA_DIR"] = str(profile_dir)
    env["SAU_COOKIE_DIR"] = str(profile_dir)

    if not click_publish or not allow_direct_publish:
        env["SHUGUANG_NOTE_XHS_REVIEW_ONLY"] = "1"
        env["REDINK_XHS_REVIEW_ONLY"] = "1"
        subprocess.Popen(command, env=env)
        print(json.dumps({
            "success": True,
            "message": "小红书发布器已启动。薯光笔记安全模式会填好内容并停在发布页，请手动检查后点击发布。",
            "command": command,
        }, ensure_ascii=False))
        return 0

    completed = subprocess.run(command, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    logs = "\n".join(part for part in [completed.stdout.strip(), completed.stderr.strip()] if part)
    print(logs)
    print(json.dumps({
        "success": completed.returncode == 0,
        "message": "小红书发布完成" if completed.returncode == 0 else None,
        "error": None if completed.returncode == 0 else logs or f"sau 退出码 {completed.returncode}",
    }, ensure_ascii=False))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
