from time import perf_counter

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Comment, Singer, Song


SONGS_PER_PAGE = 20
SINGERS_PER_PAGE = 20
SEARCH_RESULTS_PER_PAGE = 20
PAGE_BUTTON_RADIUS = 2
MAX_SEARCH_LENGTH = 20
COMMENT_USER = "匿名用户"


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

    start_page = max(1, page_obj.number - PAGE_BUTTON_RADIUS)
    end_page = min(paginator.num_pages, page_obj.number + PAGE_BUTTON_RADIUS)
    page_numbers = range(start_page, end_page + 1)

    context = {
        "page_obj": page_obj,
        "page_numbers": page_numbers,
        "keyword": keyword,
        "result_count": paginator.count,
    }

    return render(request, "songs.html", context)


def song_detail(request: HttpRequest, song_id: int) -> HttpResponse:
    """展示歌曲详情，并处理用户提交的评论。"""

    song = get_object_or_404(
        Song.objects.select_related("singer"),
        id=song_id,
    )
    comment_error = ""

    if request.method == "POST":
        content = request.POST.get("content", "").strip()

        if content:
            Comment.objects.create(
                song=song,
                user=COMMENT_USER,
                content=content,
            )
            return redirect("music:song_detail", song_id=song.id)

        comment_error = "评论内容不能为空。"

    comments = song.comments.order_by("-created_at")

    context = {
        "song": song,
        "comments": comments,
        "comment_error": comment_error,
    }

    return render(request, "song_detail.html", context)


@require_POST
def delete_comment(request: HttpRequest, comment_id: int) -> HttpResponse:
    """删除指定评论，并返回所属歌曲的详情页。"""

    comment = get_object_or_404(Comment, id=comment_id)
    song_id = comment.song_id
    comment.delete()

    return redirect("music:song_detail", song_id=song_id)


def singer_list(request: HttpRequest) -> HttpResponse:
    """分页展示系统中的全部歌手。"""

    singers = Singer.objects.order_by("id")

    paginator = Paginator(singers, SINGERS_PER_PAGE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    start_page = max(1, page_obj.number - PAGE_BUTTON_RADIUS)
    end_page = min(paginator.num_pages, page_obj.number + PAGE_BUTTON_RADIUS)
    page_numbers = range(start_page, end_page + 1)

    context = {
        "page_obj": page_obj,
        "page_numbers": page_numbers,
        "result_count": paginator.count,
    }

    return render(request, "singers.html", context)


def singer_detail(request: HttpRequest, singer_id: int) -> HttpResponse:
    """展示歌手资料及其在系统中的全部歌曲。"""

    singer = get_object_or_404(Singer, id=singer_id)
    songs = singer.songs.order_by("id")

    context = {
        "singer": singer,
        "songs": songs,
    }

    return render(request, "singer_detail.html", context)


def search(request: HttpRequest) -> HttpResponse:
    """根据用户选择搜索歌曲或歌手，并显示数量和后端耗时。"""

    keyword = request.GET.get("q", "").strip()
    search_type = request.GET.get("type", "song")
    submitted = "q" in request.GET
    search_error = ""

    if search_type not in {"song", "singer"}:
        search_type = "song"

    if submitted and not keyword:
        search_error = "请输入搜索关键词。"
    elif len(keyword) > MAX_SEARCH_LENGTH:
        search_error = f"搜索关键词不能超过{MAX_SEARCH_LENGTH}个字符。"

    page_number = request.GET.get("page")
    result_count = 0
    elapsed_ms = 0.0
    page_obj = Paginator([], SEARCH_RESULTS_PER_PAGE).get_page(1)
    page_numbers = range(1, 2)

    if submitted and not search_error:
        start_time = perf_counter()

        if search_type == "singer":
            results = Singer.objects.filter(
                Q(name__icontains=keyword)
                | Q(description__icontains=keyword)
            ).order_by("id")
        else:
            results = Song.objects.select_related("singer").filter(
                Q(name__icontains=keyword)
                | Q(singer__name__icontains=keyword)
                | Q(lyrics__icontains=keyword)
            ).order_by("id")

        paginator = Paginator(results, SEARCH_RESULTS_PER_PAGE)
        page_obj = paginator.get_page(page_number)
        result_count = paginator.count

        # 提前执行当前页查询，使计时包含数据库检索和分页取数。
        list(page_obj.object_list)

        elapsed_ms = round((perf_counter() - start_time) * 1000, 3)

        start_page = max(1, page_obj.number - PAGE_BUTTON_RADIUS)
        end_page = min(paginator.num_pages, page_obj.number + PAGE_BUTTON_RADIUS)
        page_numbers = range(start_page, end_page + 1)

    context = {
        "keyword": keyword,
        "search_type": search_type,
        "submitted": submitted,
        "search_error": search_error,
        "page_obj": page_obj,
        "page_numbers": page_numbers,
        "result_count": result_count,
        "elapsed_ms": elapsed_ms,
        "max_search_length": MAX_SEARCH_LENGTH,
    }

    return render(request, "search.html", context)