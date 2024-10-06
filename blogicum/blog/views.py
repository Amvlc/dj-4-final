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
from .post_queries import get_post_queryset
from .forms import CommentForm, EditProfileForm, PostForm
from .mixins import PostListMixin, AuthorRequiredMixin, CommentMixin
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
        # Используем get_post_queryset для получения поста
        queryset = get_post_queryset(filter_published=False)
        post = get_object_or_404(queryset, pk=self.kwargs["post_id"])

        if not post.is_published and post.author != self.request.user and not self.request.user.is_superuser:
            raise Http404("Post not found")

        return post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comments"] = self.object.comments.filter(is_published=True).select_related("author")
        context["form"] = CommentForm()
        return context


class CategoryPostListView(ListView):
    template_name = "blog/category.html"
    paginate_by = 10

    def get_queryset(self):
        now = timezone.now()
        category = get_object_or_404(Category, slug=self.kwargs["category_slug"], is_published=True)
        return get_post_queryset(manager=category.posts)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = get_object_or_404(Category, slug=self.kwargs["category_slug"], is_published=True)
        context["category"] = category 
        return context


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
    paginate_by = 10

    def get_user(self):
        """Метод для получения пользователя по имени"""
        return get_object_or_404(User, username=self.kwargs["username"])

    def get_queryset(self):
        user = self.get_user()
        return get_post_queryset(manager=Post.objects.filter(author=user), filter_published=self.request.user != user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_user()
        
        context["profile"] = user
        context["comment_count"] = Comment.objects.filter(post__author=user, is_published=True).count()
        return context


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


class EditCommentView(LoginRequiredMixin, CommentMixin, UpdateView):
    form_class = CommentForm
    template_name = "blog/create.html"


class DeleteCommentView(LoginRequiredMixin, CommentMixin, DeleteView):
    template_name = "blog/comment.html"
