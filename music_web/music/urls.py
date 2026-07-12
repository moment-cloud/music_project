from django.urls import path

from . import views


app_name = "music"

urlpatterns = [
    path("", views.song_list, name="home"),
    path("songs/", views.song_list, name="song_list"),
    path("songs/<int:song_id>/", views.song_detail, name="song_detail"),
    path(
        "comments/<int:comment_id>/delete/",
        views.delete_comment,
        name="delete_comment",
    ),
    path("singers/", views.singer_list, name="singer_list"),
    path("singers/<int:singer_id>/", views.singer_detail, name="singer_detail"),
    path("search/", views.search, name="search"),
]