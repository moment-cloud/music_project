from bs4 import BeautifulSoup


def parse_singer_html(html: str, singer_id: int, url: str) -> dict:
    """从歌手详情页HTML中提取姓名、头像和个人简介。"""

    soup = BeautifulSoup(html, "html.parser")

    result = {
        "id": singer_id,
        "name": None,
        "pic": None,
        "description": None,
        "url": url,
    }

    name_tag = soup.find("span", class_="name")

    if name_tag:
        result["name"] = name_tag.get_text(strip=True)

    # 歌手头像地址包含starheads，用它排除Logo和页面中的其他图片。
    img_tags = soup.find_all("img")

    for img in img_tags:
        src = img.get("src")

        if src and "starheads" in src:
            result["pic"] = src
            break

    title_tags = soup.find_all(class_="tit")

    for title in title_tags:
        if "个人简介" in title.get_text(strip=True):
            # 根据“个人简介”标题定位后面的正文段落。
            info = title.find_next("p", class_="info")

            if info:
                description = info.get_text(" ", strip=True)
                result["description"] = description.replace("\xa0", " ")

            break

    return result