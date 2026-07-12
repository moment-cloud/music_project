import json
import os
import random
import time

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

from singer_parser import parse_singer_html


INPUT_FILE = "data/singer_list.json"
OUTPUT_FILE = "data/singers.json"
ERROR_FILE = "data/singer_errors.txt"

HOME_URL = "https://kuwo.cn/"

PAGE_LOAD_TIMEOUT_MS = 60_000
SELECTOR_TIMEOUT_MS = 30_000
RENDER_WAIT_MS = 1_000

VIEWPORT_WIDTH = 1400
VIEWPORT_HEIGHT = 900

MIN_DELAY_SECONDS = 1.0
MAX_DELAY_SECONDS = 2.0

REQUIRED_FIELDS = ("name", "pic", "description", "url")


def load_json(filename: str) -> list[dict]:
    """读取JSON文件；文件不存在或格式错误时返回空列表。"""

    if not os.path.exists(filename):
        return []

    with open(filename, "r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return []


def save_json(data: list[dict], filename: str) -> None:
    """将数据保存为JSON文件。"""

    os.makedirs("data", exist_ok=True)

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def save_error(singer_id: int, name: str, message: str) -> None:
    """将歌手爬取失败信息追加到错误日志。"""

    os.makedirs("data", exist_ok=True)

    with open(ERROR_FILE, "a", encoding="utf-8") as file:
        file.write(f"{singer_id}\t{name}\t{message}\n")


def get_missing_fields(singer: dict) -> list[str]:
    """返回歌手数据中缺失的必需字段。"""

    missing_fields = []

    for field in REQUIRED_FIELDS:
        if not singer.get(field):
            missing_fields.append(field)

    return missing_fields


def main() -> None:
    """使用Playwright批量获取歌手详情，并支持断点续爬。"""

    singer_candidates = load_json(INPUT_FILE)

    if not singer_candidates:
        print("没有找到歌手列表：", INPUT_FILE)
        return

    # 读取已有结果，并根据歌手ID实现断点续爬。
    singers = load_json(OUTPUT_FILE)
    existing_ids = set()

    for singer in singers:
        singer_id = singer.get("id")

        if singer_id is not None:
            existing_ids.add(singer_id)

    print("候选歌手数量:", len(singer_candidates))
    print("已经完成数量:", len(existing_ids))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)

        page = browser.new_page(
            locale="zh-CN",
            viewport={
                "width": VIEWPORT_WIDTH,
                "height": VIEWPORT_HEIGHT,
            },
        )

        # 先访问首页，建立较正常的浏览器会话环境。
        try:
            page.goto(
                HOME_URL,
                wait_until="domcontentloaded",
                timeout=PAGE_LOAD_TIMEOUT_MS,
            )
            page.wait_for_timeout(RENDER_WAIT_MS)
        except PlaywrightTimeoutError:
            print("首页加载超时，继续尝试歌手详情页。")

        total = len(singer_candidates)

        for index, candidate in enumerate(singer_candidates, start=1):
            singer_id = candidate.get("id")
            name = candidate.get("name")

            if singer_id is None:
                continue

            if singer_id in existing_ids:
                print(f"[{index}/{total}] 跳过已完成：{name}")
                continue

            url = candidate.get("url")

            if not url:
                url = f"https://kuwo.cn/singer_detail/{singer_id}/info"

            try:
                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=PAGE_LOAD_TIMEOUT_MS,
                )
                page.wait_for_selector(
                    "span.name",
                    timeout=SELECTOR_TIMEOUT_MS,
                )

                # 名称出现后继续等待简介和图片等动态内容完成渲染。
                page.wait_for_timeout(RENDER_WAIT_MS)
                html = page.content()

                singer = parse_singer_html(html, singer_id, url)

                # 详情页解析失败时，使用列表中的姓名和头像作为备用数据。
                if not singer.get("name"):
                    singer["name"] = name

                if not singer.get("pic"):
                    singer["pic"] = candidate.get("pic")

                missing_fields = get_missing_fields(singer)

                if missing_fields:
                    message = "缺少字段：" + ",".join(missing_fields)
                    print(f"[{index}/{total}] 数据不完整：{name}，{message}")
                    save_error(singer_id, name, message)
                else:
                    singers.append(singer)
                    existing_ids.add(singer_id)

                    # 增量保存，程序中断后可以从已有结果继续。
                    save_json(singers, OUTPUT_FILE)

                    print(
                        f"[{index}/{total}] 成功：{singer['name']}，"
                        f"简介长度：{len(singer['description'])}"
                    )

            except PlaywrightTimeoutError:
                message = "页面加载超时"
                print(f"[{index}/{total}] 失败：{name}，{message}")
                save_error(singer_id, name, message)

            except Exception as error:
                message = str(error)
                print(f"[{index}/{total}] 失败：{name}，{message}")
                save_error(singer_id, name, message)

            # 降低请求频率，避免短时间内连续访问服务器。
            time.sleep(
                random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
            )

        browser.close()

    print("==============================")
    print("歌手详情保存数量:", len(singers))
    print("保存位置:", OUTPUT_FILE)
    print("失败记录:", ERROR_FILE)
    print("==============================")


if __name__ == "__main__":
    main()