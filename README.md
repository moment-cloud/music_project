# 酷我音乐数据采集与展示系统

## 项目说明

本项目从酷我音乐采集歌手、歌曲和歌词数据，对数据进行清洗和去重，
并使用 Django 和 SQLite 实现歌曲浏览、歌手浏览、搜索和评论功能。

## 数据处理流程

1. `crawler/singer_list_spider.py` 获取候选歌手列表。
2. `crawler/singer_spider.py` 使用 Playwright 加载歌手详情页。
3. `crawler/singer_parser.py` 解析歌手姓名、头像和简介。
4. `crawler/song_list_spider.py` 获取各歌手的歌曲列表。
5. `crawler/song_lyric_spider.py` 获取并清洗歌词。
6. `music_web/import_data.py` 将最终 JSON 数据导入 SQLite。
7. Django 的 views 从数据库查询数据并交给 templates 渲染。

## 主要目录

- `crawler/`：数据采集与清洗代码
- `music_web/`：Django 网站
- `analysis/`：数据分析代码与结果
- `validate_crawler_data.py`：数据完整性验证程序

## 安装依赖

```powershell
pip install -r requirements.txt