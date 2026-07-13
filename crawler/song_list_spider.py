import json
import os
import random
import time

import requests

from config import COOKIE, SECRET


INPUT_FILE = "data/singers.json"
OUTPUT_FILE = "data/song_candidates.json"

API_URL = "https://www.kuwo.cn/api/www/artist/artistMusic"
SONG_DETAIL_URL = "https://www.kuwo.cn/play_detail/{rid}"

SONGS_PER_SINGER = 25
REQUEST_COUNT = 30
REQUEST_PAGE = 1
REQUEST_TIMEOUT_SECONDS = 15

MIN_DELAY_SECONDS = 1.0
MAX_DELAY_SECONDS = 2.0
FAILED_REQUEST_DELAY_SECONDS = 2.0

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/144.0.0.0 Safari/537.36"
)


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

def get_artist_songs(singer_id: int) -> list[dict]:
    """调用酷我接口，获取指定歌手的歌曲列表。"""

    params = {
        "artistid": singer_id,
        "pn": REQUEST_PAGE,
        "rn": REQUEST_COUNT,
        "httpsStatus": "1",
        "plat": "web_www",
    }

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": f"https://www.kuwo.cn/singer_detail/{singer_id}",
        "Accept": "application/json, text/plain, */*",
        "Secret": SECRET,
        "Cookie": COOKIE,
    }

    response = requests.get(
        API_URL,
        params=params,
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    data = response.json()
    return data.get("data", {}).get("list", [])


def main() -> None:
    """为每名歌手获取25首候选歌曲，并支持断点续爬。"""

    singers = load_json(INPUT_FILE)

    if not singers:
        print("没有找到歌手数据：", INPUT_FILE)
        return

    # 读取已有结果，重建每名歌手的进度和候选歌曲去重集合。
    song_candidates = load_json(OUTPUT_FILE)
    saved_count = {}
    existing_keys = set()

    # 候选阶段按“歌手ID + 歌曲RID”去重，暂时保留跨歌手的合唱歌曲。
    for song in song_candidates:
        singer_id = song.get("singer_id")
        rid = song.get("rid")

        if singer_id is None or rid is None:
            continue

        singer_id = int(singer_id)
        rid = int(rid)
        key = (singer_id, rid)

        if key in existing_keys:
            continue

        existing_keys.add(key)
        saved_count[singer_id] = saved_count.get(singer_id, 0) + 1

    print("歌手数量:", len(singers))
    print("已有歌曲候选数量:", len(song_candidates))

    total = len(singers)

    for index, singer in enumerate(singers, start=1):
        singer_id = singer.get("id")
        singer_name = singer.get("name")

        if singer_id is None:
            continue

        singer_id = int(singer_id)
        current_count = saved_count.get(singer_id, 0)

        if current_count >= SONGS_PER_SINGER:
            print(
                f"[{index}/{total}] 跳过已完成：{singer_name}，"
                f"已有{current_count}首"
            )
            continue

        try:
            artist_songs = get_artist_songs(singer_id)
        except (requests.RequestException, ValueError) as error:
            print(f"[{index}/{total}] 失败：{singer_name}，{error}")
            time.sleep(FAILED_REQUEST_DELAY_SECONDS)
            continue

        added_count = 0

        for song in artist_songs:
            if current_count + added_count >= SONGS_PER_SINGER:
                break

            rid = song.get("rid")
            name = song.get("name")

            if rid is None or not name:
                continue

            rid = int(rid)
            key = (singer_id, rid)

            if key in existing_keys:
                continue

            candidate = {
                "rid": rid,
                "name": name,
                "singer_id": singer_id,
                "singer_name": singer_name,
                "artist": song.get("artist"),
                "album": song.get("album"),
                "pic": song.get("pic"),
                "duration": song.get("duration"),
                "source_url": SONG_DETAIL_URL.format(rid=rid),
            }

            song_candidates.append(candidate)
            existing_keys.add(key)
            added_count += 1

        saved_count[singer_id] = current_count + added_count

        # 增量保存，程序中断后可以从已有结果继续。
        save_json(song_candidates, OUTPUT_FILE)

        print(
            f"[{index}/{total}] {singer_name}：新增{added_count}首，"
            f"当前共{saved_count[singer_id]}首，总候选{len(song_candidates)}首"
        )

        time.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))

    print("==============================")
    print("歌曲候选总数:", len(song_candidates))
    print("保存位置:", OUTPUT_FILE)
    print("==============================")


if __name__ == "__main__":
    main()