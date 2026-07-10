def parse_music_info(data):

    music = data["data"]

    result = {
        "name": music.get("name"),
        "artist": music.get("artist"),
        "album": music.get("album"),
        "duration": music.get("duration"),
        "pic": music.get("pic"),
        "releaseDate": music.get("releaseDate"),
        "rid": music.get("rid")
    }

    return result


if __name__ == "__main__":

    test = {
    "data": {
        "name": "新地球",
        "artist": "林俊杰",
        "album": "新地球",
        "duration": 277,
        "pic": "test.jpg",
        "releaseDate": "2014-12-27",
        "rid": 197473417
    }
}

    print(parse_music_info(test))