from django.contrib import admin
from .models import UserProfile, VideoParsingRecord

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'points', 'last_login_reward_date')
    search_fields = ('user__username',)

@admin.register(VideoParsingRecord)
class VideoParsingRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'video_url', 'created_at')
    search_fields = ('user__username', 'video_url')
    list_filter = ('created_at',)
