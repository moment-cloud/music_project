from django.db import models


class Singer(models.Model):
    """保存歌手基本资料。"""

    kuwo_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=200)
    pic = models.URLField(max_length=500)
    description = models.TextField()
    source_url = models.URLField(max_length=500)

    def __str__(self) -> str:
        return self.name


class Song(models.Model):
    """保存歌曲信息及其所属歌手。"""

    rid = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=300)
    singer = models.ForeignKey(
        Singer,
        on_delete=models.CASCADE,
        related_name="songs",
    )
    artist = models.CharField(max_length=300, blank=True)
    album = models.CharField(max_length=300, blank=True)
    duration = models.IntegerField(null=True, blank=True)
    pic = models.URLField(max_length=500, blank=True)
    lyrics = models.TextField()
    source_url = models.URLField(max_length=500)

    def __str__(self) -> str:
        return self.name


class Comment(models.Model):
    """保存用户对歌曲的评论。"""

    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.CharField(max_length=50)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.user}：{self.content[:20]}"