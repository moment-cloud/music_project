from spider import get_search_result
from spider import get_music_info
from save import save_json
from parser import parse_music_info

import time

search_data = get_search_result("林俊杰")


songs = search_data["abslist"]

result = []

for song in songs[:5]:

    musicrid = song["MUSICRID"]

    mid = musicrid.replace("MUSIC_", "")

    print("正在获取:", song["NAME"])

    info = get_music_info(mid)

    music = parse_music_info(info)

    result.append(music)

    time.sleep(2)

save_json(
    result,
    "data/songs.json"
)

print("保存完成")