from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('profile/', views.user_profile, name='profile'),
    path('parse-video/', views.parse_video, name='parse_video'),
    path('download-video/<int:record_id>/', views.download_video, name='download_video'),
] 