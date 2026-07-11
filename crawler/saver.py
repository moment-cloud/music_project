import json


def save_music(music, filename):

    with open(filename, "w", encoding="utf-8") as f:

        json.dump(
            music,
            f,
            ensure_ascii=False,
            indent=4
        )


if __name__ == "__main__":

    test_music = {
        "name": "新地球",
        "artist": "林俊杰"
    }

    save_music(
        test_music,
        "data/test.json"
    )


def save_json(data, filename):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )