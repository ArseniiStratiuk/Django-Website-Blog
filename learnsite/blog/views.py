from django.shortcuts import render, redirect
from .models import Post, Profile, Comment, Category
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from .forms import ProfileForm, AddCommentForm, RegisterForm
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views.generic.list import ListView
from django.views.generic import DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .utils import *
from django.urls import reverse


class PostListMain(DataMixin, ListView):
    model = Post  # All posts in object_list.
    context_object_name = "posts"
    template_name = "blog_main.html"
    paginate_by = 4

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mix_context = self.get_user_context()
        context['slide_posts'] = Post.objects.all()
        context.update(mix_context)
        return context
    
    def get_queryset(self):
        search_query = self.request.GET.get("searchpost")
        if search_query:
            return Post.objects.filter(Q(title__icontains=search_query.lower()) |
                                Q(title__icontains=search_query.capitalize()) | 
                                Q(title__icontains=search_query.upper())
            ).prefetch_related('views_number')
        return Post.objects.all().prefetch_related('views_number')
    

class ShowPost(DataMixin, LoginRequiredMixin, DetailView):
    login_url = '/login'
    redirect_field_name = 'redirect_to'
    model = Post
    template_name = 'post_view.html'
    slug_url_kwargs = 'slug'
    context_object_name = 'post'

    def get_object(self):
        slug = self.kwargs['slug']
        obj_post = Post.objects.get(post_slug=slug)
        return obj_post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            if not context['post'].views_number.filter(id=self.request.user.id).exists():
                context['post'].views_number.add(self.request.user)
                
        context['views_num'] = context['post'].get_views_number()
        context['likes_num'] = context['post'].get_likes_number()
        context['is_liked'] = context['post'].likes.filter(id=self.request.user.id).exists()
        context['is_saved'] = context['post'].saves.filter(id=self.request.user.id).exists()
        context['comments'] = Comment.objects.filter(post=context['post'])
        context['comment_form'] = AddCommentForm()

        mix_context = self.get_user_context()

        return {**context, **mix_context}

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = AddCommentForm(request.POST)
        if form.is_valid():
            content = request.POST.get('content')
            comment = Comment.objects.create(post=self.object, author=request.user, content=content)
            comment.save()
            return redirect(f'/{self.object.post_slug}')
        return self.get(request, *args, **kwargs)


class UserRegistration(CreateView):
    form_class = RegisterForm
    template_name = 'register.html'
    success_url = '/'

    def form_valid(self, form):
        username = "New User"
        messages.success(self.request, f"Створено новий акаунт: {username}")
        return super().form_valid(form)


@login_required
def profile(request):
    if request.method == 'POST':
        profile_form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Профіль оновлено')
            return redirect(to='user_profile')
    else:
        try:
            request.user.profile
        except Profile.DoesNotExist:
            Profile.objects.create(user=request.user).save()
        finally:
            profile_form = ProfileForm(instance=request.user.profile)

    profile = request.user.profile
    return render(request, 'profile.html', {
        'profile': profile,
        'profile_form': profile_form
    })
    
def look_profile(request, username):
    look_for = Profile.objects.get(user__username=username)
    if look_for == request.user.profile:
        return redirect(to='user_profile')
    else:
        return render(request, 'look_profile.html', {'profile': look_for})
    
def like_post(request, post_id):
    """
    Add one like for one post per user.
    """
    post = Post.objects.get(id=post_id)
    if post.likes.filter(id=request.user.id).exists():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
    return redirect(f'/{post.post_slug}') 

def save_post(request, post_id):
    """
    Add one save for one post per user.
    """
    post = Post.objects.get(id=post_id)
    if post.saves.filter(id=request.user.id).exists():
        post.saves.remove(request.user)
    else:
        post.saves.add(request.user)
    return redirect(f'/{post.post_slug}') 

def show_saved_post(request):
    """
    Show user's saved posts.
    """
    posts = Post.objects.all()
    sidebar = Category.objects.all()
    page = request.GET.get('page')
    saved_posts = request.user.post_save.all()
    paginator = Paginator(saved_posts, 4)
    try:
        data_page = paginator.page(page)
    except PageNotAnInteger:
        data_page = paginator.page(1)
    except EmptyPage:
        data_page = paginator.page(paginator.num_pages)
    data_dict  ={
        "slide_posts": posts,
        "posts": data_page,
        "sidebar": sidebar
    }
    return render(request, 'blog_main.html', data_dict)

def search_post(request):
    """
    Functionality for navbar to process search form.
    """
    sidebar = Category.objects.all()
    all_posts = Post.objects.all()
    page = request.GET.get('page')
    posts = None
    if request.method == "POST":
        text = request.POST.get("searchpost")
        posts = Post.objects.filter(
            Q(title__icontains=text.lower()) | 
            Q(title__icontains=text.capitalize()) | 
            Q(title__icontains=text.upper())
        )

    data_dict  ={
        "slide_posts": all_posts,
        "posts": posts,
        "sidebar": sidebar
    }
    return render(request, 'blog_main.html', data_dict)

def get_comment_form(request, post):
    """
    Post user's comment, form processing.
    """
    if request.method == "POST":
        form = AddCommentForm(request.POST)
        if form.is_valid():
            content = request.POST.get('content')
            comment = Comment.objects.create(post=post, author=request.user, content=content)
            comment.save()
        return redirect(f'/{post.post_slug}')
    else:
        form = AddCommentForm()
    return form

def slug_process(request, slug):
    """
    Search URL in category slugs first and if no matching, 
    then search URL in post slugs. In both cases show sidebar 
    with categories.
    """
    sidebar = Category.objects.all()
    categories = [ c.category_slug for c in sidebar]
    if slug in categories:
        category_posts = Post.objects.filter(category__category_slug=slug).prefetch_related('views_number')
        return render(request, "category.html", {
            "posts" : category_posts, 
            "sidebar": sidebar
        })
        
    post_slugs = [p.post_slug for p in Post.objects.all()]
    if slug in post_slugs:
        post = Post.objects.get(post_slug = slug)
        if request.user.is_authenticated:
            if not post.views_number.filter(id=request.user.id).exists():
                post.views_number.add(request.user)
                
        views = post.get_views_number()
        likes = post.get_likes_number()
        is_liked = post.likes.filter(id=request.user.id).exists()
        is_saved = post.saves.filter(id=request.user.id).exists()
        comments = Comment.objects.filter(post=post)
        form = get_comment_form(request, post)
        data_dict = { 'post': post, 
                      'views_num': views, 
                      'likes_num': likes, 
                      'comment_form': form, 
                      'comments': comments, 
                      'is_liked': is_liked, 
                      'is_saved': is_saved, 
                      'sidebar': sidebar }
        return render(request, 'post_view.html', data_dict)

def register(request):
    # POST incoming
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            username = form.cleaned_data.get("username")
            messages.success(request, f"Створено новий акаунт: {username}")
            return redirect("/")
        else:
            print("ERROR DURING REGISTRATION!+")
            for msg in form.error_messages:
                messages.error(request, f"{msg}")
            return render(request, 'register.html', {'form': form})

    # GET incoming
    data_dict = {"form": RegisterForm}
    return render(request, 'register.html', data_dict)

def logout_request(request):
    logout(request)
    messages.info(request, "Ви вийшли з акаунту")
    return redirect("/")

def login_request(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Ви успішно увійшли, {username}")
                return redirect("/")
            else:
                for msg in form.error_messages:
                    messages.error(request, f"Помилка, неправильний {msg}")
                return redirect("/login")
    form = AuthenticationForm()
    return render(request, "login.html", {"form": form})
