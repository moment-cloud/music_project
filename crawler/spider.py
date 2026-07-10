import requests
from config import SECRET, COOKIE
from urllib.parse import quote

def get_music_info(mid):

    url = "https://kuwo.cn/api/www/music/musicInfo"

    params = {
        "mid": mid,
        "httpsStatus": "1",
        "plat": "web_www"
    }

    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/150.0.0.0",

        "Secret":SECRET,

        "Cookie":COOKIE
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

    except requests.RequestException as e:
        print("请求失败:", e)
        return None
    try:
        return response.json()

    except Exception:
        print("JSON解析失败")
        return None

def get_search_result(keyword):

    url = "https://kuwo.cn/search/searchMusicBykeyWord"

    params = {
        "vipver": "1",
        "client": "kt",
        "ft": "music",
        "cluster": "0",
        "strategy": "2012",
        "encoding": "utf8",
        "rformat": "json",
        "mobi": "1",
        "issubtitle": "1",
        "show_copyright_off": "1",
        "pn": "0",
        "rn": "20",
        "all": keyword
    }


    headers = {

        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",

        "Referer":
        "https://kuwo.cn/search/list?key=" + quote(keyword),

        "Accept":
        "application/json, text/plain, */*",

        "Cookie":COOKIE
    }


    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

    except requests.RequestException as e:
        print("请求失败:", e)
        return None
    
    print(response.status_code)

    try:
        return response.json()

    except Exception:
        print("JSON解析失败")
        return None

    


if __name__ == "__main__":

    data = get_music_info(197473417)

    print(data["data"]["name"])
    print(data["data"]["artist"])