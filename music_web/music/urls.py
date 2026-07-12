from django.urls import path

from . import views


app_name = "music"

urlpatterns = [
    path("", views.song_list, name="home"),
    path("songs/", views.song_list, name="song_list"),
]