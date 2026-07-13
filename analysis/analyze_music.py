import csv
import json
import logging
import re
from collections import Counter, defaultdict
from pathlib import Path

import jieba
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "songs_full.json"
OUTPUT_DIR = PROJECT_ROOT / "analysis" / "output"

TOP_WORDS_PER_SINGER = 5
CHART_WORD_COUNT = 15
CHART_SINGER_COUNT = 20

STOPWORDS = {
    "的", "了", "着", "过", "地", "得", "和", "与", "或", "而", "但", "却",
    "也", "都", "又", "还", "很", "更", "最", "太", "再", "才", "就", "把",
    "被", "让", "给", "在", "从", "到", "对", "向", "是", "有", "没有", "没",
    "无", "不", "不是", "我", "你", "他", "她", "它", "我们", "你们", "他们",
    "自己", "这", "那", "这里", "那里", "一个", "什么", "怎么", "为什么",
    "如果", "因为", "所以", "只是", "就是", "还是", "已经", "不会", "不能",
    "不要", "可以", "能够", "无法", "然后", "这样", "一样", "时候", "现在",
    "今天", "明天", "所有", "一切", "那么", "这么", "起来", "下去", "回来",
    "知道", "看到", "听到", "觉得", "想要", "为了", "还有", "只有", "也许",
    "呢", "吗", "啊", "呀", "吧", "哦", "喔", "啦", "嘛", "哎", "唉", "嗯",
    "来", "去", "谁", "哪", "何",
    "oh", "yeah", "baby", "la", "na", "hey", "woo", "ooh", "ah", "ha", "hmm",
    "the", "a", "an", "and", "to", "of", "in", "on", "is", "are", "i", "you",
    "me", "my", "we", "it", "that", "this", "for", "with", "be", "do", "dont",
    "im", "your", "no",
}

CREDIT_LINE_RE = re.compile(
    r"^(作词|词|作曲|曲|编曲|制作人|监制|演唱|歌手|合声|和声|"
    r"吉他|贝斯|鼓|键盘|弦乐|录音|混音|母带|策划|统筹|"
    r"出品|发行|op|sp)\s*[:：]",
    re.IGNORECASE,
)

RIGHTS_LINE_RE = re.compile(
    r"(未经许可|不得翻唱|版权所有|本歌曲来自|酷我音乐)",
    re.IGNORECASE,
)

BRACKET_TAG_RE = re.compile(r"\[[^\]]*\]")

VERSION_BRACKET_RE = re.compile(
    r"[\(（\[【][^)\）\]】]*"
    r"(live|remix|伴奏|现场|demo|版本|纯音乐)"
    r"[^)\）\]】]*[\)）\]】]",
    re.IGNORECASE,
)

TRAILING_VERSION_RE = re.compile(
    r"\s*[-—–]\s*(live|remix|伴奏|现场版|demo|纯音乐版).*$",
    re.IGNORECASE,
)


def load_songs() -> tuple[int, list[dict]]:
    """读取歌曲，并按照 rid 去重。"""
    raw_songs = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    unique_songs = {}

    for song in raw_songs:
        rid = str(song.get("rid", "")).strip()
        if rid and rid not in unique_songs:
            unique_songs[rid] = song

    return len(raw_songs), list(unique_songs.values())


def normalize_text(text: str) -> str:
    """转为小写，并删除标点和空白。"""
    return re.sub(
        r"[\W_]+",
        "",
        str(text).lower(),
        flags=re.UNICODE,
    )


def clean_title(title: str) -> str:
    """删除标题中的 Live、Remix、伴奏等版本说明。"""
    title = VERSION_BRACKET_RE.sub("", str(title))
    title = TRAILING_VERSION_RE.sub("", title)
    return title.strip()


def clean_lyrics(song: dict) -> str:
    """删除歌词中的歌曲标题行、制作人员和版权信息。"""
    title_key = normalize_text(clean_title(song.get("name", "")))
    singer_key = normalize_text(song.get("singer_name", ""))
    cleaned_lines = []

    for index, raw_line in enumerate(
        str(song.get("lyrics", "")).splitlines()
    ):
        line = BRACKET_TAG_RE.sub("", raw_line).strip()

        if not line:
            continue

        line_key = normalize_text(line)

        is_header = (
            index < 3
            and title_key
            and singer_key
            and title_key in line_key
            and singer_key in line_key
        )

        if is_header:
            continue

        if CREDIT_LINE_RE.match(line):
            continue

        if RIGHTS_LINE_RE.search(line):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def tokenize(text: str) -> list[str]:
    """使用 jieba 分词，并删除停用词、数字和符号。"""
    words = []

    for token in jieba.lcut(text):
        word = normalize_text(token)

        if not word:
            continue

        if word in STOPWORDS:
            continue

        if word.isdigit():
            continue

        if word.isascii() and len(word) < 2:
            continue

        words.append(word)

    return words


def write_csv(
    filename: str,
    fieldnames: list[str],
    rows: list[dict],
) -> None:
    """将统计结果保存为 CSV 文件。"""
    path = OUTPUT_DIR / filename

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def analyze_singer_top_words(
    songs: list[dict],
) -> Counter:
    """统计每位歌手歌词中出现次数最多的五个词。"""
    singer_counters = defaultdict(Counter)
    singer_song_counts = Counter()

    for song in songs:
        singer = str(song.get("singer_name", "")).strip()
        singer = singer or "未知歌手"

        singer_song_counts[singer] += 1
        singer_counters[singer].update(song["_tokens"])

    rows = []
    top_word_presence = Counter()

    for singer in sorted(singer_counters):
        top_words = singer_counters[singer].most_common(
            TOP_WORDS_PER_SINGER
        )

        for rank, (word, count) in enumerate(
            top_words,
            start=1,
        ):
            rows.append(
                {
                    "singer": singer,
                    "song_count": singer_song_counts[singer],
                    "rank": rank,
                    "word": word,
                    "count": count,
                }
            )

            top_word_presence[word] += 1

    write_csv(
        "singer_top_words.csv",
        [
            "singer",
            "song_count",
            "rank",
            "word",
            "count",
        ],
        rows,
    )

    return top_word_presence


def analyze_title_occurrences(
    songs: list[dict],
) -> tuple[list[dict], dict]:
    """统计标题在对应歌词中的出现次数。"""
    singer_stats = defaultdict(
        lambda: {
            "song_count": 0,
            "songs_with_title": 0,
            "total_occurrences": 0,
        }
    )

    song_rows = []

    for song in songs:
        singer = str(song.get("singer_name", "")).strip()
        singer = singer or "未知歌手"

        title = clean_title(song.get("name", ""))
        title_key = normalize_text(title)
        lyrics_key = normalize_text(song["_clean_lyrics"])

        if title_key:
            occurrences = lyrics_key.count(title_key)
        else:
            occurrences = 0

        song_rows.append(
            {
                "rid": song.get("rid", ""),
                "singer": singer,
                "title": song.get("name", ""),
                "clean_title": title,
                "occurrences": occurrences,
                "appeared": int(occurrences > 0),
            }
        )

        stats = singer_stats[singer]
        stats["song_count"] += 1
        stats["songs_with_title"] += int(occurrences > 0)
        stats["total_occurrences"] += occurrences

    singer_rows = []

    for singer, stats in singer_stats.items():
        song_count = stats["song_count"]

        singer_rows.append(
            {
                "singer": singer,
                "song_count": song_count,
                "songs_with_title": stats["songs_with_title"],
                "title_appearance_rate": round(
                    stats["songs_with_title"]
                    / song_count
                    * 100,
                    2,
                ),
                "total_occurrences": stats["total_occurrences"],
                "average_occurrences_per_song": round(
                    stats["total_occurrences"]
                    / song_count,
                    3,
                ),
            }
        )

    singer_rows.sort(
        key=lambda row: (
            row["title_appearance_rate"],
            row["average_occurrences_per_song"],
        ),
        reverse=True,
    )

    overall = {
        "song_count": len(song_rows),
        "songs_with_title": sum(
            row["appeared"] for row in song_rows
        ),
        "total_occurrences": sum(
            row["occurrences"] for row in song_rows
        ),
    }

    overall["title_appearance_rate"] = round(
        overall["songs_with_title"]
        / overall["song_count"]
        * 100,
        2,
    )

    write_csv(
        "song_title_occurrences.csv",
        [
            "rid",
            "singer",
            "title",
            "clean_title",
            "occurrences",
            "appeared",
        ],
        song_rows,
    )

    write_csv(
        "singer_title_summary.csv",
        [
            "singer",
            "song_count",
            "songs_with_title",
            "title_appearance_rate",
            "total_occurrences",
            "average_occurrences_per_song",
        ],
        singer_rows,
    )

    return singer_rows, overall


def analyze_keyword_title_overlap(
    songs: list[dict],
) -> dict:
    """判断每首歌的 Top 1 和 Top 3 高频词是否出现在标题中。"""
    rows = []
    top1_match_count = 0
    top3_match_count = 0

    for song in songs:
        counter = Counter(song["_tokens"])

        top_words = [
            word
            for word, _ in counter.most_common(3)
        ]

        title = clean_title(song.get("name", ""))
        title_key = normalize_text(title)

        top1_match = bool(
            top_words
            and top_words[0] in title_key
        )

        top3_match = any(
            word in title_key
            for word in top_words
        )

        top1_match_count += int(top1_match)
        top3_match_count += int(top3_match)

        rows.append(
            {
                "rid": song.get("rid", ""),
                "singer": song.get("singer_name", ""),
                "title": song.get("name", ""),
                "top1_word": (
                    top_words[0]
                    if top_words
                    else ""
                ),
                "top3_words": "、".join(top_words),
                "top1_match": int(top1_match),
                "top3_match": int(top3_match),
            }
        )

    song_count = len(rows)

    summary = {
        "song_count": song_count,
        "top1_match_count": top1_match_count,
        "top3_match_count": top3_match_count,
        "top1_match_rate": round(
            top1_match_count / song_count * 100,
            2,
        ),
        "top3_match_rate": round(
            top3_match_count / song_count * 100,
            2,
        ),
    }

    write_csv(
        "keyword_title_overlap.csv",
        [
            "rid",
            "singer",
            "title",
            "top1_word",
            "top3_words",
            "top1_match",
            "top3_match",
        ],
        rows,
    )

    return summary


def plot_common_top_words(
    top_word_presence: Counter,
) -> None:
    """绘制进入最多歌手 Top 5 的词语。"""
    items = top_word_presence.most_common(
        CHART_WORD_COUNT
    )

    words = [
        word
        for word, _ in reversed(items)
    ]

    counts = [
        count
        for _, count in reversed(items)
    ]

    plt.figure(figsize=(10, 7))
    bars = plt.barh(words, counts)

    plt.xlabel("进入该词 Top 5 的歌手数量")
    plt.ylabel("词语")
    plt.title("进入最多歌手歌词 Top 5 的词语")

    for bar, count in zip(bars, counts):
        plt.text(
            count + 0.1,
            bar.get_y() + bar.get_height() / 2,
            str(count),
            va="center",
        )

    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "top_words_across_singers.png",
        dpi=200,
    )
    plt.close()


def plot_title_appearance_rates(
    singer_rows: list[dict],
) -> None:
    """绘制标题出现率最高的歌手。"""
    selected = singer_rows[:CHART_SINGER_COUNT]

    singers = [
        row["singer"]
        for row in reversed(selected)
    ]

    rates = [
        row["title_appearance_rate"]
        for row in reversed(selected)
    ]

    plt.figure(figsize=(11, 8))
    bars = plt.barh(singers, rates)

    plt.xlabel("标题在歌词中出现的歌曲比例（%）")
    plt.ylabel("歌手")
    plt.title(
        f"标题出现率最高的 "
        f"{CHART_SINGER_COUNT} 位歌手"
    )
    plt.xlim(0, 100)

    for bar, rate in zip(bars, rates):
        plt.text(
            min(rate + 0.5, 98),
            bar.get_y() + bar.get_height() / 2,
            f"{rate:.1f}%",
            va="center",
        )

    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "title_appearance_rate.png",
        dpi=200,
    )
    plt.close()


def plot_keyword_title_overlap(
    summary: dict,
) -> None:
    """绘制歌词高频词和标题的重合率。"""
    labels = [
        "Top 1 高频词",
        "Top 3 中至少一个词",
    ]

    rates = [
        summary["top1_match_rate"],
        summary["top3_match_rate"],
    ]

    plt.figure(figsize=(7, 5))
    bars = plt.bar(labels, rates)

    plt.ylabel("与标题重合的歌曲比例（%）")
    plt.title("歌词高频词与歌曲标题的重合率")
    plt.ylim(0, 100)

    for bar, rate in zip(bars, rates):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            rate + 1,
            f"{rate:.2f}%",
            ha="center",
        )

    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "keyword_title_overlap.png",
        dpi=200,
    )
    plt.close()


def write_summary(
    raw_count: int,
    songs: list[dict],
    top_word_presence: Counter,
    title_overall: dict,
    overlap_summary: dict,
) -> None:
    """保存实验报告需要引用的统计结果。"""
    common_words = "、".join(
        f"{word}（{count}位歌手）"
        for word, count
        in top_word_presence.most_common(10)
    )

    singer_count = len(
        {
            song.get("singer_name", "")
            for song in songs
        }
    )

    lines = [
        f"原始歌曲数：{raw_count}",
        f"按 rid 去重后的歌曲数：{len(songs)}",
        f"歌手数：{singer_count}",
        "",
        "问题一：不同歌手歌词高频词",
        f"进入最多歌手 Top 5 的词语：{common_words}",
        "",
        "问题二：标题在歌词中的出现情况",
        (
            "标题出现过的歌曲数："
            f"{title_overall['songs_with_title']}"
        ),
        (
            "标题出现率："
            f"{title_overall['title_appearance_rate']:.2f}%"
        ),
        (
            "标题总出现次数："
            f"{title_overall['total_occurrences']}"
        ),
        "",
        "问题三：高频词与标题的重合情况",
        (
            "Top 1 高频词重合歌曲数："
            f"{overlap_summary['top1_match_count']}"
        ),
        (
            "Top 1 高频词重合率："
            f"{overlap_summary['top1_match_rate']:.2f}%"
        ),
        (
            "Top 3 至少一个词重合歌曲数："
            f"{overlap_summary['top3_match_count']}"
        ),
        (
            "Top 3 至少一个词重合率："
            f"{overlap_summary['top3_match_rate']:.2f}%"
        ),
    ]

    summary_path = OUTPUT_DIR / "analysis_summary.txt"

    summary_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    jieba.setLogLevel(logging.WARNING)

    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    raw_count, songs = load_songs()

    for song in songs:
        song["_clean_lyrics"] = clean_lyrics(song)
        song["_tokens"] = tokenize(
            song["_clean_lyrics"]
        )

    top_word_presence = analyze_singer_top_words(
        songs
    )

    singer_title_rows, title_overall = (
        analyze_title_occurrences(songs)
    )

    overlap_summary = (
        analyze_keyword_title_overlap(songs)
    )

    plot_common_top_words(top_word_presence)
    plot_title_appearance_rates(
        singer_title_rows
    )
    plot_keyword_title_overlap(
        overlap_summary
    )

    write_summary(
        raw_count,
        songs,
        top_word_presence,
        title_overall,
        overlap_summary,
    )

    print(
        f"分析完成，结果保存在：{OUTPUT_DIR}"
    )
    print(f"原始歌曲数：{raw_count}")
    print(f"去重后歌曲数：{len(songs)}")
    print(
        "标题出现率："
        f"{title_overall['title_appearance_rate']:.2f}%"
    )
    print(
        "Top 1 高频词重合率："
        f"{overlap_summary['top1_match_rate']:.2f}%"
    )
    print(
        "Top 3 高频词重合率："
        f"{overlap_summary['top3_match_rate']:.2f}%"
    )


if __name__ == "__main__":
    main()