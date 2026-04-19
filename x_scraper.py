"""
X (Twitter) 内容抓取模块
使用 Playwright 自动化浏览器登录X并搜索感兴趣的话题内容

注意: 由于 X 对自动化工具有较强的检测机制，
推荐使用 Cursor 内置浏览器 (MCP browser) 进行交互式抓取。
本脚本作为命令行备用方案保留。
"""

import os
import time
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from dotenv import load_dotenv

load_dotenv()

X_USERNAME = os.getenv("X_USERNAME")
X_PASSWORD = os.getenv("X_PASSWORD")
TOPICS = [t.strip() for t in os.getenv("TOPICS", "").split(",") if t.strip()]
TOPICS_CN = [t.strip() for t in os.getenv("TOPICS_CN", "").split(",") if t.strip()]
TWEETS_PER_TOPIC = int(os.getenv("TWEETS_PER_TOPIC", "20"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./reports")


def _debug_screenshot(page, name):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"{name}.png")
    page.screenshot(path=path)
    print(f"  [debug] 截图: {path}")


def login_to_x(page):
    """登录X账号"""
    print("[*] 打开X登录页面...")
    page.goto("https://x.com/i/flow/login", timeout=60000)
    time.sleep(8)
    _debug_screenshot(page, "step1_initial")

    print("[*] 输入用户名...")
    username_input = None
    for selector in ['input[name="text"]', 'input[autocomplete="username"]']:
        try:
            loc = page.locator(selector).first
            if loc.is_visible(timeout=5000):
                username_input = loc
                break
        except (PlaywrightTimeout, Exception):
            continue

    if not username_input:
        print("[-] 未找到用户名输入框")
        return False

    username_input.click()
    time.sleep(0.3)
    username_input.type(X_USERNAME, delay=80)
    time.sleep(1)

    print("[*] 点击下一步...")
    for text in ["Next", "下一步", "next"]:
        try:
            btn = page.get_by_role("button", name=text, exact=False)
            if btn.is_visible(timeout=2000):
                btn.click()
                break
        except (PlaywrightTimeout, Exception):
            continue
    time.sleep(5)

    # 处理可能的验证步骤
    try:
        v_input = page.locator('input[data-testid="ocfEnterTextTextInput"]')
        if v_input.is_visible(timeout=3000):
            print("[!] 需要额外验证...")
            v_input.fill(X_USERNAME)
            page.locator('button[data-testid="ocfEnterTextNextButton"]').click()
            time.sleep(5)
    except (PlaywrightTimeout, Exception):
        pass

    print("[*] 输入密码...")
    pw_input = None
    for selector in ['input[name="password"]', 'input[type="password"]']:
        try:
            loc = page.locator(selector)
            if loc.is_visible(timeout=5000):
                pw_input = loc
                break
        except (PlaywrightTimeout, Exception):
            continue

    if not pw_input:
        _debug_screenshot(page, "login_no_password")
        print("[-] 未找到密码输入框")
        return False

    pw_input.click()
    pw_input.type(X_PASSWORD, delay=80)
    time.sleep(1)

    print("[*] 点击登录...")
    try:
        page.locator('button[data-testid="LoginForm_Login_Button"]').click()
    except Exception:
        pw_input.press("Enter")
    time.sleep(8)

    if "home" in page.url:
        print("[+] 登录成功！")
        return True

    try:
        page.wait_for_url("**/home", timeout=15000)
        print("[+] 登录成功！")
        return True
    except PlaywrightTimeout:
        _debug_screenshot(page, "login_failed")
        print(f"[-] 登录失败，URL: {page.url}")
        return False


def search_topic(page, topic, max_tweets=20):
    """搜索话题并抓取推文"""
    print(f"\n[*] 搜索: {topic}")
    tweets = []
    page.goto(
        f"https://x.com/search?q={topic}&src=typed_query&f=top",
        wait_until="networkidle",
        timeout=30000,
    )
    time.sleep(3)

    for scroll in range(10):
        if len(tweets) >= max_tweets:
            break
        articles = page.locator('article[data-testid="tweet"]')
        for i in range(articles.count()):
            if len(tweets) >= max_tweets:
                break
            try:
                art = articles.nth(i)
                data = _extract(art)
                if data and data.get("text") and data["text"] not in [t["text"] for t in tweets]:
                    data["search_topic"] = topic
                    tweets.append(data)
            except Exception:
                continue
        page.evaluate("window.scrollBy(0, 1000)")
        time.sleep(2)

    print(f"  [+] '{topic}' → {len(tweets)} 条")
    return tweets


def _extract(article):
    """提取推文数据"""
    t = {}
    try:
        links = article.locator('a[role="link"][href*="/"]')
        if links.count() > 0:
            href = links.first.get_attribute("href")
            if href:
                t["author"] = href.strip("/").split("/")[-1]

        name_el = article.locator('div[data-testid="User-Name"] span').first
        if name_el.is_visible():
            t["display_name"] = name_el.inner_text()

        text_el = article.locator('div[data-testid="tweetText"]')
        if text_el.count() > 0:
            t["text"] = text_el.first.inner_text()
        else:
            return None

        time_el = article.locator("time")
        if time_el.count() > 0:
            t["time"] = time_el.first.get_attribute("datetime")

        t["metrics"] = {}
        for m in ["reply", "retweet", "like"]:
            el = article.locator(f'button[data-testid="{m}"] span')
            if el.count() > 0:
                t["metrics"][m] = el.first.inner_text() or "0"

        tweet_links = article.locator('a[href*="/status/"]')
        if tweet_links.count() > 0:
            href = tweet_links.first.get_attribute("href")
            if href and "/status/" in href:
                t["url"] = f"https://x.com{href}" if not href.startswith("http") else href
    except Exception:
        pass
    return t


def run_scraper():
    """运行抓取流程"""
    all_topics = TOPICS + TOPICS_CN
    if not all_topics:
        print("[-] 没有配置搜索话题")
        return None

    all_tweets = {}
    today = datetime.now().strftime("%Y-%m-%d")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="en-US",
        )
        ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        page = ctx.new_page()

        if not login_to_x(page):
            browser.close()
            return None

        for topic in all_topics:
            try:
                all_tweets[topic] = search_topic(page, topic, TWEETS_PER_TOPIC)
            except Exception as e:
                print(f"[-] '{topic}' 出错: {e}")
                all_tweets[topic] = []
            time.sleep(2)

        browser.close()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    raw_path = os.path.join(OUTPUT_DIR, f"raw_{today}.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(all_tweets, f, ensure_ascii=False, indent=2)
    print(f"\n[+] 原始数据: {raw_path}")
    return all_tweets


if __name__ == "__main__":
    data = run_scraper()
    if data:
        total = sum(len(v) for v in data.values())
        print(f"\n[+] 完成！共 {total} 条推文")
