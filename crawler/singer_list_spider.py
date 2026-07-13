import json
import os
import time

import requests

from config import SECRET, COOKIE


API_URL = (
    "https://www.kuwo.cn/"
    "api/www/artist/artistInfo"
)

OUTPUT_FILE = "data/singer_list.json"

TARGET_COUNT = 100
PAGE_SIZE = 60


def get_singer_page(page_number):
    """
    获取一页歌手列表。
    """

    params = {
        "category": "0",
        "prefix": "",
        "pn": page_number,
        "rn": PAGE_SIZE,
        "httpsStatus": "1",
        "plat": "web_www"
    }

    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/144.0.0.0 Safari/537.36",

        "Referer":
        "https://www.kuwo.cn/singers",

        "Accept":
        "application/json, text/plain, */*",

        "Secret":
        SECRET,

        "Cookie":
        COOKIE
    }

    response = requests.get(
        API_URL,
        params=params,
        headers=headers,
        timeout=15
    )

    print(
        f"第{page_number}页状态码:",
        response.status_code
    )

    response.raise_for_status()

    data = response.json()

    artist_list = (
        data
        .get("data", {})
        .get("artistList", [])
    )

    return artist_list


def save_singer_list(singers):
    """
    将歌手列表保存成JSON文件。
    """

    os.makedirs(
        "data",
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            singers,
            file,
            ensure_ascii=False,
            indent=2
        )


def main():
    singers = []

    seen_ids = set()

    # 最多请求3页
    for page_number in range(1, 4):

        artist_list = get_singer_page(
            page_number
        )

        print(
            f"第{page_number}页原始歌手数量:",
            len(artist_list)
        )

        if not artist_list:

            print(
                "这一页没有歌手数据，停止请求。"
            )

            break

        for artist in artist_list:

            singer_id = artist.get("id")
            name = artist.get("name")

            if singer_id is None or not name:
                continue

            singer_id = int(singer_id)

            if singer_id in seen_ids:
                continue

            singer = {
                "id": singer_id,

                "name": name,

                "pic": (
                    artist.get("pic300")
                    or artist.get("pic120")
                    or artist.get("pic")
                ),

                "url": (
                    "https://kuwo.cn/"
                    f"singer_detail/{singer_id}/info"
                )
            }

            singers.append(singer)

            seen_ids.add(singer_id)


            if len(singers) >= TARGET_COUNT:
                break

        print(
            "当前有效歌手数量:",
            len(singers)
        )

        if len(singers) >= TARGET_COUNT:
            break

        time.sleep(1)

    save_singer_list(singers)

    print("==============================")
    print("最终歌手数量:", len(singers))
    print("保存位置:", OUTPUT_FILE)
    print("==============================")


    for singer in singers[:10]:

        print(
            singer["id"],
            singer["name"]
        )


    if len(singers) < TARGET_COUNT:

        print(
            "警告：歌手数量不足100。"
        )


if __name__ == "__main__":

    main()