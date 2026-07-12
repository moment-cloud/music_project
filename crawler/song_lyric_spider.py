import json
import os
import random
import re
import time

import requests

from config import COOKIE, SECRET


INPUT_FILE = "data/song_candidates.json"
OUTPUT_FILE = "data/songs_full.json"
ERROR_FILE = "data/song_lyric_errors.txt"
DEBUG_FILE = "data/lyric_debug.json"

LYRIC_API = "https://www.kuwo.cn/openapi/v1/www/lyric/getlyric"

REQUEST_TIMEOUT_SECONDS = 15
RETRY_COUNT = 2
RETRY_DELAY_MIN_SECONDS = 0.8
RETRY_DELAY_MAX_SECONDS = 1.2
REQUEST_DELAY_MIN_SECONDS = 1.0
REQUEST_DELAY_MAX_SECONDS = 1.5
FAILED_REQUEST_DELAY_SECONDS = 2.0

VERIFY_SAMPLE_COUNT = 5
MAX_CONSECUTIVE_ERRORS = 5
SAVE_INTERVAL = 10
PRINT_INTERVAL = 25
MIN_REQUIRED_SONGS = 2000
MIN_REQUIRED_SINGERS = 100

BRACKET_TAG_PATTERN = r"\[[^\]]*\]"

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


def save_json(data: list | dict, filename: str) -> None:
    """将Python数据保存为JSON文件。"""

    os.makedirs("data", exist_ok=True)

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def save_error(candidate: dict, message: str) -> None:
    """将无歌词或请求失败的歌曲追加到错误日志。"""

    os.makedirs("data", exist_ok=True)

    with open(ERROR_FILE, "a", encoding="utf-8") as file:
        file.write(
            f"{candidate.get('rid')}\t{candidate.get('singer_name')}\t"
            f"{candidate.get('name')}\t{message}\n"
        )


def request_lyric_data(rid: int) -> dict:
    """请求一首歌曲的歌词JSON；失败时自动重试一次。"""

    params = {
        "musicId": rid,
        "httpsStatus": "1",
        "plat": "web_www",
    }

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": f"https://www.kuwo.cn/play_detail/{rid}",
        "Accept": "application/json, text/plain, */*",
        "Secret": SECRET,
        "Cookie": COOKIE,
    }

    last_error = None

    for attempt in range(RETRY_COUNT):
        try:
            response = requests.get(
                LYRIC_API,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()

        except (requests.RequestException, ValueError) as error:
            last_error = error

            if attempt < RETRY_COUNT - 1:
                delay = random.uniform(
                    RETRY_DELAY_MIN_SECONDS,
                    RETRY_DELAY_MAX_SECONDS,
                )
                time.sleep(delay)

    if last_error is not None:
        raise last_error

    raise RuntimeError("歌词请求失败，但没有获得具体异常信息。")


def clean_lyric_line(line: str) -> str:
    """删除一行歌词中的时间戳和其他方括号标签。"""

    return re.sub(BRACKET_TAG_PATTERN, "", line).strip()


def extract_lyrics(data: dict) -> tuple[str, bool]:
    """提取纯文本歌词，并返回是否识别到接口数据结构。"""

    if not isinstance(data, dict):
        return "", False

    data_part = data.get("data")

    # 请求成功但data为空，表示歌曲没有可用歌词。
    if data_part == {}:
        return "", True

    lyric_list = None
    raw_lyric = None

    # 常见结构：{"data": {"lrclist": [...]}} 或 {"data": {"lyric": "..."}}
    if isinstance(data_part, dict):
        if "lrclist" in data_part:
            lyric_list = data_part.get("lrclist")
        elif "lyric" in data_part:
            raw_lyric = data_part.get("lyric")

    # 兼容歌词字段直接位于最外层的返回结构。
    if lyric_list is None and "lrclist" in data:
        lyric_list = data.get("lrclist")

    if raw_lyric is None and "lyric" in data:
        raw_lyric = data.get("lyric")

    if isinstance(lyric_list, list):
        lines = []

        for item in lyric_list:
            if not isinstance(item, dict):
                continue

            line = str(item.get("lineLyric") or "").strip()
            line = clean_lyric_line(line)

            if line:
                lines.append(line)

        return "\n".join(lines), True

    if isinstance(raw_lyric, str):
        lines = []

        for line in raw_lyric.splitlines():
            line = clean_lyric_line(line)

            if line:
                lines.append(line)

        return "\n".join(lines), True

    if lyric_list == [] or raw_lyric == "":
        return "", True

    return "", False


def verify_lyric_api(candidates: list[dict]) -> bool:
    """正式爬取前抽样验证歌词接口和返回结构。"""

    print("正在验证歌词接口……")

    for candidate in candidates[:VERIFY_SAMPLE_COUNT]:
        rid = candidate.get("rid")

        if rid is None:
            continue

        try:
            data = request_lyric_data(int(rid))
        except (requests.RequestException, ValueError) as error:
            print("测试请求失败:", candidate.get("name"), error)
            continue

        lyrics, structure_found = extract_lyrics(data)

        if structure_found:
            print(
                "歌词接口验证成功：",
                candidate.get("name"),
                "歌词长度：",
                len(lyrics),
            )
            return True

        # 保存一次无法识别的响应，避免继续发送大量无效请求。
        save_json(data, DEBUG_FILE)
        print("歌词接口返回了JSON，但数据结构无法识别。")
        print("响应已保存到：", DEBUG_FILE)
        return False

    print(f"前{VERIFY_SAMPLE_COUNT}首歌曲都无法验证歌词接口，程序停止。")
    return False


def main() -> None:
    """批量获取候选歌曲歌词，清理时间标签并保存有效歌曲。"""

    candidates = load_json(INPUT_FILE)

    if not candidates:
        print("没有找到歌曲候选数据：", INPUT_FILE)
        return

    songs = load_json(OUTPUT_FILE)

    # 已成功保存的歌曲使用“歌手ID + 歌曲RID”实现断点续爬。
    existing_keys = set()

    for song in songs:
        singer_id = song.get("singer_id")
        rid = song.get("rid")

        if singer_id is None or rid is None:
            continue

        existing_keys.add((int(singer_id), int(rid)))

    print("候选歌曲数量:", len(candidates))
    print("已经完成数量:", len(songs))

    if not verify_lyric_api(candidates):
        return

    success_count = len(songs)
    no_lyric_count = 0
    request_error_count = 0
    consecutive_errors = 0
    total = len(candidates)

    for index, candidate in enumerate(candidates, start=1):
        singer_id = candidate.get("singer_id")
        rid = candidate.get("rid")

        if singer_id is None or rid is None:
            continue

        singer_id = int(singer_id)
        rid = int(rid)
        key = (singer_id, rid)

        if key in existing_keys:
            continue

        try:
            data = request_lyric_data(rid)
            consecutive_errors = 0

        except (requests.RequestException, ValueError) as error:
            request_error_count += 1
            consecutive_errors += 1
            save_error(candidate, "请求失败：" + str(error))

            # 连续失败通常表示网络、Cookie或接口状态出现整体性问题。
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                save_json(songs, OUTPUT_FILE)
                print(
                    f"连续{MAX_CONSECUTIVE_ERRORS}次请求失败，"
                    "为避免无效请求，程序已停止。"
                )
                print("当前有效歌曲数量:", len(songs))
                return

            time.sleep(FAILED_REQUEST_DELAY_SECONDS)
            continue

        lyrics, structure_found = extract_lyrics(data)

        if not structure_found:
            save_json(data, DEBUG_FILE)
            save_json(songs, OUTPUT_FILE)
            print("发现无法识别的歌词响应，程序已停止。")
            print("调试数据位置:", DEBUG_FILE)
            return

        if not lyrics:
            no_lyric_count += 1
            save_error(candidate, "无歌词")
        else:
            # 复制候选字典，避免直接修改原始候选数据。
            song = candidate.copy()
            song["singer_id"] = singer_id
            song["rid"] = rid
            song["lyrics"] = lyrics

            songs.append(song)
            existing_keys.add(key)
            success_count += 1

        if index % SAVE_INTERVAL == 0:
            save_json(songs, OUTPUT_FILE)

        if index % PRINT_INTERVAL == 0:
            print(
                f"[{index}/{total}] 有效歌曲：{success_count}，"
                f"无歌词：{no_lyric_count}，"
                f"请求失败：{request_error_count}"
            )

        delay = random.uniform(
            REQUEST_DELAY_MIN_SECONDS,
            REQUEST_DELAY_MAX_SECONDS,
        )
        time.sleep(delay)

    save_json(songs, OUTPUT_FILE)

    singer_ids = set()

    for song in songs:
        singer_id = song.get("singer_id")

        if singer_id is not None:
            singer_ids.add(int(singer_id))

    print("==============================")
    print("有效歌曲数量:", len(songs))
    print("覆盖歌手数量:", len(singer_ids))
    print("无歌词歌曲数量:", no_lyric_count)
    print("请求失败数量:", request_error_count)
    print("保存位置:", OUTPUT_FILE)
    print("==============================")

    if len(songs) < MIN_REQUIRED_SONGS:
        print("当前有效歌曲不足2000首，需要继续补充歌曲。")

    if len(singer_ids) < MIN_REQUIRED_SINGERS:
        print("当前没有覆盖全部100名歌手，需要补充缺失歌手的数据。")


if __name__ == "__main__":
    main()