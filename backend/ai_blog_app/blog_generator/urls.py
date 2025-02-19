from django.urls import path, include
from . import views

urlpatterns = [
# Landing Page
path('', views.index, name='index'),
#login
path('login', views.user_login, name='login'),
#signup
path('signup', views.user_signup, name='signup'),
#logout
path('logout', views.user_logout, name='logout'),
#Blog Generate
path('generate-blog', views.generate_blog, name='generate-blog'),
#Blog Lists
path('blog-list', views.blog_list, name='blog-list'),
#Blog Details
path('blog-details/<int:pk>/', views.blog_details, name='blog-details'),
]