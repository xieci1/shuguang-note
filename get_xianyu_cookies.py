from playwright.sync_api import sync_playwright
from pathlib import Path
import os
import time
import shutil

TARGET_URL = "https://www.goofish.com"
OUTPUT_FILE = Path("xianyu_cookies.txt")


def find_browser_path():
    """
    自动查找 Windows 上已安装的 Chrome / Edge。
    优先 Chrome，其次 Edge。
    """
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]

    for path in possible_paths:
        if Path(path).exists():
            return path

    # 尝试从系统 PATH 查找
    chrome = shutil.which("chrome")
    if chrome:
        return chrome

    edge = shutil.which("msedge")
    if edge:
        return edge

    return None


def build_cookie_string(cookies):
    """
    转成 XianyuAutoAgent 可用格式：
    name=value; name2=value2
    """
    allow_domains = [
        "goofish.com",
        "taobao.com",
        "tmall.com",
        "alibaba.com",
        "aliyun.com",
        "mmstat.com",
        "alipay.com",
    ]

    result = []
    seen = set()

    for c in cookies:
        domain = c.get("domain", "")
        name = c.get("name", "")
        value = c.get("value", "")

        if not name or value is None:
            continue

        if not any(d in domain for d in allow_domains):
            continue

        # 按 name 去重
        if name in seen:
            continue

        seen.add(name)
        result.append(f"{name}={value}")

    return "; ".join(result)


def main():
    browser_path = find_browser_path()

    if not browser_path:
        print("没有找到 Chrome 或 Edge 浏览器。")
        print("请确认你已经安装 Chrome 或 Edge。")
        return

    print("找到浏览器：")
    print(browser_path)
    print()
    print("即将打开浏览器。")
    print("请在打开的浏览器里登录闲鱼。")
    print("登录成功后，回到这个窗口按回车。")
    print("注意：Cookie 等同登录凭证，不要发给别人，不要截图外泄。")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=browser_path,
            headless=False,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = browser.new_context(
            viewport=None,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/148.0.0.0 Safari/537.36"
            ),
        )

        page = context.new_page()
        page.goto(TARGET_URL, wait_until="domcontentloaded")

        input("登录闲鱼成功后，回到这里按回车继续获取 Cookie...")

        # 登录后再刷新一次，确保 Cookie 写入
        try:
            page.goto(TARGET_URL, wait_until="networkidle", timeout=30000)
            time.sleep(2)
        except Exception:
            pass

        cookies = context.cookies()
        cookie_str = build_cookie_string(cookies)

        browser.close()

    if not cookie_str:
        print()
        print("没有获取到 Cookie。")
        print("请确认你已经在打开的浏览器里成功登录闲鱼。")
        return

    OUTPUT_FILE.write_text(cookie_str, encoding="utf-8")

    print()
    print("获取成功！")
    print(f"Cookie 已保存到：{OUTPUT_FILE.resolve()}")
    print()
    print("复制下面这一整行到 XianyuAutoAgent 的 .env：")
    print()
    print("COOKIES_STR=" + cookie_str)
    print()
    print("也可以直接打开 xianyu_cookies.txt 复制里面内容。")


if __name__ == "__main__":
    main()