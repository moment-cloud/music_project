import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parent
SINGERS_FILE = PROJECT_ROOT / "data" / "singers.json"
SONGS_FILE = PROJECT_ROOT / "data" / "songs_full.json"

TIME_TAG_PATTERN = re.compile(r"\[\d{1,3}:\d{2}(?:\.\d+)?\]")
BRACKET_TAG_PATTERN = re.compile(r"\[[^\]]*\]")

MEDIA_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".wav",
    ".aac",
    ".m4a",
    ".ogg",
    ".mp4",
    ".mkv",
    ".avi",
    ".webm",
}

MEDIA_KEYWORDS = {
    "audio",
    "video",
    "stream_url",
    "play_url",
    "download_url",
    "mp3_url",
    "mv_url",
}


def load_json_list(filename: Path) -> list[dict]:
    """读取JSON列表，并检查文件顶层结构。"""

    with filename.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"{filename} 的顶层结构不是列表。")

    return data


def to_int(value) -> int | None:
    """尽量把值转换为整数。"""

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def has_text(value) -> bool:
    """判断值是否为非空字符串。"""

    return isinstance(value, str) and bool(value.strip())


def is_http_url(value) -> bool:
    """判断值是否为HTTP或HTTPS地址。"""

    if not has_text(value):
        return False

    return value.startswith(("http://", "https://"))


def contains_media_url(item: dict) -> bool:
    """检查一条数据是否包含音频或视频地址。"""

    for key, value in item.items():
        key_lower = str(key).lower()

        if value and any(word in key_lower for word in MEDIA_KEYWORDS):
            return True

        if isinstance(value, str) and value.startswith(("http://", "https://")):
            suffix = Path(urlparse(value).path).suffix.lower()

            if suffix in MEDIA_EXTENSIONS:
                return True

    return False


def print_result(label: str, passed: bool, detail: str) -> None:
    """打印一项验证结果。"""

    status = "通过" if passed else "未通过"
    print(f"[{status}] {label}：{detail}")


def main() -> None:
    """验证爬虫数据是否满足课程的核心要求。"""

    singers = load_json_list(SINGERS_FILE)
    raw_songs = load_json_list(SONGS_FILE)

    singer_ids = []
    invalid_singer_ids = 0
    missing_singer_fields = Counter()
    invalid_singer_urls = Counter()

    for singer in singers:
        singer_id = to_int(singer.get("id"))

        if singer_id is None:
            invalid_singer_ids += 1
        else:
            singer_ids.append(singer_id)

        required_fields = {
            "name": singer.get("name"),
            "pic": singer.get("pic"),
            "description": singer.get("description"),
            "url": singer.get("url"),
        }

        for field, value in required_fields.items():
            if not has_text(value):
                missing_singer_fields[field] += 1

        if has_text(singer.get("pic")) and not is_http_url(singer.get("pic")):
            invalid_singer_urls["pic"] += 1

        if has_text(singer.get("url")) and not is_http_url(singer.get("url")):
            invalid_singer_urls["url"] += 1

    singer_id_counts = Counter(singer_ids)
    duplicate_singer_ids = sum(
        count - 1 for count in singer_id_counts.values() if count > 1
    )
    singer_id_set = set(singer_ids)

    unique_songs = []
    seen_rids = set()
    duplicate_song_count = 0
    invalid_rid_count = 0

    for song in raw_songs:
        rid = to_int(song.get("rid"))

        if rid is None:
            invalid_rid_count += 1
            continue

        if rid in seen_rids:
            duplicate_song_count += 1
            continue

        seen_rids.add(rid)
        unique_songs.append(song)

    missing_song_fields = Counter()
    invalid_song_urls = Counter()
    unknown_singer_references = 0
    covered_singer_ids = set()
    time_tag_song_count = 0
    other_bracket_tag_count = 0
    media_data_count = 0

    for song in unique_songs:
        singer_id = to_int(song.get("singer_id"))
        singer_name = song.get("singer_name") or song.get("artist")

        required_fields = {
            "name": song.get("name"),
            "singer_name": singer_name,
            "lyrics": song.get("lyrics"),
            "pic": song.get("pic"),
            "source_url": song.get("source_url"),
        }

        for field, value in required_fields.items():
            if not has_text(value):
                missing_song_fields[field] += 1

        if singer_id is None or singer_id not in singer_id_set:
            unknown_singer_references += 1
        else:
            covered_singer_ids.add(singer_id)

        pic = song.get("pic")
        source_url = song.get("source_url")
        lyrics = song.get("lyrics") or ""

        if has_text(pic) and not is_http_url(pic):
            invalid_song_urls["pic"] += 1

        if has_text(source_url) and not is_http_url(source_url):
            invalid_song_urls["source_url"] += 1

        if TIME_TAG_PATTERN.search(lyrics):
            time_tag_song_count += 1

        if BRACKET_TAG_PATTERN.search(lyrics):
            other_bracket_tag_count += 1

        if contains_media_url(song):
            media_data_count += 1

    uncovered_singers = singer_id_set - covered_singer_ids

    print("============ 数据概况 ============")
    print("原始歌手数量:", len(singers))
    print("有效歌手ID数量:", len(singer_id_set))
    print("原始歌曲数量:", len(raw_songs))
    print("重复歌曲数量:", duplicate_song_count)
    print("去重后歌曲数量:", len(unique_songs))
    print("歌曲覆盖歌手数量:", len(covered_singer_ids))
    print()

    print("============ 考核验证 ============")

    print_result(
        "歌手数量不少于100",
        len(singer_id_set) >= 100,
        f"{len(singer_id_set)}名",
    )
    print_result(
        "去重后歌曲数量不少于2000",
        len(unique_songs) >= 2000,
        f"{len(unique_songs)}首",
    )
    print_result(
        "每位歌手至少有一首歌曲",
        not uncovered_singers and len(covered_singer_ids) >= 100,
        f"覆盖{len(covered_singer_ids)}名，未覆盖{len(uncovered_singers)}名",
    )
    print_result(
        "歌手ID合法且不重复",
        invalid_singer_ids == 0 and duplicate_singer_ids == 0,
        f"非法{invalid_singer_ids}条，重复{duplicate_singer_ids}条",
    )
    print_result(
        "歌手必需字段完整",
        not missing_singer_fields,
        str(dict(missing_singer_fields)),
    )
    print_result(
        "歌曲必需字段完整",
        not missing_song_fields,
        str(dict(missing_song_fields)),
    )
    print_result(
        "歌曲均能关联现有歌手",
        unknown_singer_references == 0,
        f"异常关联{unknown_singer_references}条",
    )
    print_result(
        "歌手图片和原始URL格式正常",
        not invalid_singer_urls,
        str(dict(invalid_singer_urls)),
    )
    print_result(
        "歌曲图片和原始URL格式正常",
        not invalid_song_urls,
        str(dict(invalid_song_urls)),
    )
    print_result(
        "歌词没有残留时间标签",
        time_tag_song_count == 0,
        f"发现{time_tag_song_count}首",
    )
    print_result(
        "没有保存音频或视频地址",
        media_data_count == 0,
        f"发现{media_data_count}条可疑数据",
    )

    print()
    print("============ 补充信息 ============")
    print("无效歌曲RID数量:", invalid_rid_count)
    print("仍含其他方括号文本的歌曲数量:", other_bracket_tag_count)

    if uncovered_singers:
        print("未覆盖歌手ID示例:", sorted(uncovered_singers)[:10])

    core_passed = (
        len(singer_id_set) >= 100
        and len(unique_songs) >= 2000
        and not uncovered_singers
        and invalid_singer_ids == 0
        and duplicate_singer_ids == 0
        and not missing_singer_fields
        and not missing_song_fields
        and unknown_singer_references == 0
        and not invalid_singer_urls
        and not invalid_song_urls
        and time_tag_song_count == 0
        and media_data_count == 0
    )

    print()
    if core_passed:
        print("最终结论：爬虫数据满足课程核心数据要求。")
    else:
        print("最终结论：仍有未通过项目，暂时不要提交最终数据。")


if __name__ == "__main__":
    main()