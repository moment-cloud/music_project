from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .models import Song


SONGS_PER_PAGE = 20


def song_list(request: HttpRequest) -> HttpResponse:
    """展示歌曲列表，并支持关键词搜索和分页。"""

    # 同时查询关联歌手，避免为每首歌曲额外执行一次数据库查询。
    songs = Song.objects.select_related("singer").order_by("id")

    keyword = request.GET.get("q", "").strip()

    if keyword:
        songs = songs.filter(
            Q(name__icontains=keyword)
            | Q(singer__name__icontains=keyword)
            | Q(lyrics__icontains=keyword)
        )

    paginator = Paginator(songs, SONGS_PER_PAGE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "keyword": keyword,
        "result_count": paginator.count,
    }

    return render(request, "songs.html", context)