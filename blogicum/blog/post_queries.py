from .models import Post
from django.db.models import Count


def get_post_queryset(
    manager=Post.objects, filter_published=True, annotate_comments=True
):
    queryset = manager.select_related("author", "category", "location")

    if filter_published:
        queryset = queryset.filter(published=True)

    if annotate_comments:
        queryset = queryset.annotate(comment_count=Count("comments"))

    return queryset
