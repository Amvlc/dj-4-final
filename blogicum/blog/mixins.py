from django.db.models import Count, Q
from django.utils import timezone

from .const import PAGINATE_BY
from .models import Post


class PostListMixin:
    model = Post
    paginate_by = PAGINATE_BY

    def get_queryset(self):
        return get_post_queryset(
            self.model.objects.all(),
            filter_published=True,
            annotate_comments=True,
        )


def get_post_queryset(manager, filter_published=True, annotate_comments=True):
    queryset = manager.select_related()
    if filter_published:
        queryset = queryset.filter(
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now(),
        )
    if annotate_comments:
        queryset = queryset.annotate(
            comment_count=Count(
                "comments", filter=Q(comments__is_published=True)
            )
        ).order_by("-pub_date")
    return queryset
