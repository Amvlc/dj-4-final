from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import Http404

from .forms import CommentForm, EditProfileForm, PostForm
from .mixins import PostListMixin
from .models import Comment, Post, Category

User = get_user_model()


class PostListView(PostListMixin, ListView):
    template_name = "blog/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comment_counts"] = {
            post.id: post.comments.count() for post in self.object_list}
        return context


class PostDetailView(DetailView):
    model = Post
    template_name = "blog/detail.html"

    def get_object(self, queryset=None):
        post = get_object_or_404(
            Post.objects.select_related("author"), pk=self.kwargs["post_id"]
        )

        if (
            not post.is_published
            and post.author != self.request.user
            and not self.request.user.is_superuser
        ):
            raise Http404("Post not found")

        return post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comments"] = Comment.objects.filter(
            post=self.object, is_published=True
        ).select_related("author")
        context["form"] = CommentForm()
        return context


class CategoryPostListView(ListView):
    template_name = "blog/category.html"

    def get_queryset(self):
        now = timezone.now()
        category = get_object_or_404(
            Category, slug=self.kwargs["category_slug"])
        if not category.is_published:
            raise Http404("Category not found")
        return Post.objects.filter(
            category=category,
            is_published=True,
            pub_date__lte=now,
        ).select_related("author")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_obj"] = self.get_paginated_queryset(self.get_queryset())
        return context

    def get_paginated_queryset(self, queryset):
        paginator = Paginator(queryset, 10)
        page_number = self.request.GET.get("page")
        return paginator.get_page(page_number)


class CreatePostView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = "blog/create.html"

    def form_valid(self, form):
        post = form.save(commit=False)
        post.author = self.request.user
        post.save()
        return redirect("blog:profile", username=self.request.user.username)


class AuthorRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        obj = self.get_object()
        return obj.author == self.request.user


class EditPostView(LoginRequiredMixin, AuthorRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = "blog/create.html"
    pk_url_kwarg = "post_id"

    def handle_no_permission(self):
        return redirect("blog:post_detail", post_id=self.kwargs["post_id"])


class DeletePostView(LoginRequiredMixin, AuthorRequiredMixin, DeleteView):
    model = Post
    template_name = (
        "blog/delete.html"
    )
    pk_url_kwarg = "post_id"

    def get_success_url(self):
        return reverse(
            "blog:profile", kwargs={"username": self.request.user.username}
        )


class ProfileView(ListView):
    template_name = "blog/profile.html"

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs["username"])
        return Post.objects.filter(
            author=user
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_object_or_404(User, username=self.kwargs["username"])
        context["profile"] = user
        context["page_obj"] = self.get_paginated_queryset(self.get_queryset())
        context["comment_count"] = Comment.objects.filter(
            post__author=user).count()
        if self.request.user.is_authenticated and self.request.user == user:
            pass
        return context

    def get_paginated_queryset(self, queryset):
        paginator = Paginator(queryset, 10)
        page_number = self.request.GET.get("page")
        return paginator.get_page(page_number)


class EditProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = EditProfileForm
    template_name = "blog/user.html"

    def get_object(self):
        return self.request.user

    def get_success_url(self):
        return reverse(
            "blog:profile", kwargs={"username": self.request.user.username}
        )


class AddCommentView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = "blog/detail.html"

    def form_valid(self, form):
        post = get_object_or_404(Post, id=self.kwargs["post_id"])
        comment = form.save(commit=False)
        comment.post = post
        comment.author = self.request.user
        comment.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "blog:post_detail", kwargs={"post_id": self.kwargs["post_id"]}
        )


class EditCommentView(LoginRequiredMixin, AuthorRequiredMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = "blog/create.html"

    def get_object(self):
        return get_object_or_404(
            Comment,
            id=self.kwargs["comment_id"],
            post_id=self.kwargs["post_id"],
        )

    def get_success_url(self):
        return reverse(
            "blog:post_detail", kwargs={"post_id": self.kwargs["post_id"]}
        )


class DeleteCommentView(LoginRequiredMixin, AuthorRequiredMixin, DeleteView):
    model = Comment
    template_name = "blog/comment.html"

    def get_object(self):
        return get_object_or_404(
            Comment,
            id=self.kwargs["comment_id"],
            post_id=self.kwargs["post_id"],
        )

    def get_success_url(self):
        return reverse(
            "blog:post_detail", kwargs={"post_id": self.kwargs["post_id"]}
        )
