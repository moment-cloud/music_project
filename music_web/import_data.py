import json
import os
import re

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_web.settings")
django.setup()

from django.db import transaction

from music.models import Comment, Singer, Song


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SINGERS_FILE = os.path.join(PROJECT_ROOT, "data", "singers.json")
SONGS_FILE = os.path.join(PROJECT_ROOT, "data", "songs_full.json")

BRACKET_TAG_PATTERN = r"\[[^\]]*\]"
BATCH_SIZE = 500

MIN_SINGER_COUNT = 100
MIN_SONG_COUNT = 2000
MIN_COVERED_SINGER_COUNT = 100


def load_json(filename: str) -> list[dict]:
    """读取指定JSON文件。"""

    with open(filename, "r", encoding="utf-8") as file:
        return json.load(file)


def clean_lyrics(lyrics: str) -> str:
    """清除歌词中残余的方括号标签和空行。"""

    lyrics = re.sub(BRACKET_TAG_PATTERN, "", lyrics)
    lines = []

    for line in lyrics.splitlines():
        line = line.strip()

        if line:
            lines.append(line)

    return "\n".join(lines)


def parse_duration(value: int | str | None) -> int | None:
    """将歌曲时长转换为整数，转换失败时返回None。"""

    if value is None or value == "":
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    """清洗爬虫数据并批量导入Django数据库。"""

    print("正在读取本地JSON文件……")

    singer_data = load_json(SINGERS_FILE)
    song_data = load_json(SONGS_FILE)

    print("原始歌手数量:", len(singer_data))
    print("原始歌曲数量:", len(song_data))

    singer_rows = []
    seen_singer_ids = set()

    for item in singer_data:
        singer_id = item.get("id")
        name = item.get("name")
        pic = item.get("pic")
        description = item.get("description")
        source_url = item.get("url")

        if (
            singer_id is None
            or not name
            or not pic
            or not description
            or not source_url
        ):
            continue

        singer_id = int(singer_id)

        if singer_id in seen_singer_ids:
            continue

        singer_rows.append(
            Singer(
                kuwo_id=singer_id,
                name=name,
                pic=pic,
                description=description,
                source_url=source_url,
            )
        )
        seen_singer_ids.add(singer_id)

    with transaction.atomic():
        Comment.objects.all().delete()
        Song.objects.all().delete()
        Singer.objects.all().delete()

        Singer.objects.bulk_create(singer_rows, batch_size=BATCH_SIZE)

        # 将酷我歌手ID映射到数据库歌手对象，供歌曲建立外键。
        singer_map = {}

        for singer in Singer.objects.all():
            singer_map[singer.kuwo_id] = singer

        song_rows = []
        seen_rids = set()
        covered_singer_ids = set()

        duplicate_count = 0
        invalid_count = 0

        for item in song_data:
            rid = item.get("rid")
            name = item.get("name")
            singer_id = item.get("singer_id")
            lyrics = item.get("lyrics")
            source_url = item.get("source_url")

            if (
                rid is None
                or not name
                or singer_id is None
                or not lyrics
                or not source_url
            ):
                invalid_count += 1
                continue

            rid = int(rid)
            singer_id = int(singer_id)

            # 同一首合唱歌曲可能来自多个歌手列表，最终按照RID保留一次。
            if rid in seen_rids:
                duplicate_count += 1
                continue

            singer = singer_map.get(singer_id)

            if singer is None:
                invalid_count += 1
                continue

            lyrics = clean_lyrics(lyrics)

            if not lyrics:
                invalid_count += 1
                continue

            artist = item.get("artist") or item.get("singer_name") or singer.name
            album = item.get("album") or ""
            pic = item.get("pic") or ""
            duration = parse_duration(item.get("duration"))

            song_rows.append(
                Song(
                    rid=rid,
                    name=name,
                    singer=singer,
                    artist=artist,
                    album=album,
                    duration=duration,
                    pic=pic,
                    lyrics=lyrics,
                    source_url=source_url,
                )
            )

            seen_rids.add(rid)
            covered_singer_ids.add(singer_id)

        print("去重后待导入歌曲数量:", len(song_rows))
        print("重复歌曲数量:", duplicate_count)
        print("无效歌曲数量:", invalid_count)

        if len(singer_rows) < MIN_SINGER_COUNT:
            raise RuntimeError("有效歌手不足100名，取消导入。")

        if len(song_rows) < MIN_SONG_COUNT:
            raise RuntimeError("去重后歌曲不足2000首，取消导入。")

        if len(covered_singer_ids) < MIN_COVERED_SINGER_COUNT:
            raise RuntimeError("歌曲没有覆盖全部100名歌手，取消导入。")

        Song.objects.bulk_create(song_rows, batch_size=BATCH_SIZE)

    final_singer_count = Singer.objects.count()
    final_song_count = Song.objects.count()
    covered_count = Song.objects.values("singer_id").distinct().count()

    print("==============================")
    print("数据库歌手数量:", final_singer_count)
    print("数据库歌曲数量:", final_song_count)
    print("歌曲覆盖歌手数量:", covered_count)
    print("==============================")
    print("数据库导入成功，数据要求已满足。")


if __name__ == "__main__":
    main()