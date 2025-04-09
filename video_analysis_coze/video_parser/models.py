from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    points = models.IntegerField(default=10, verbose_name='积分')
    last_login_reward_date = models.DateField(null=True, blank=True, verbose_name='上次登录奖励日期')
    
    def __str__(self):
        return f"{self.user.username}的个人资料"
    
    class Meta:
        verbose_name = '用户资料'
        verbose_name_plural = '用户资料'

# 当用户注册时自动创建资料
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if not hasattr(instance, 'profile'):
        UserProfile.objects.create(user=instance)
    instance.profile.save()

class VideoParsingRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parsing_records')
    video_url = models.URLField(verbose_name='视频URL')
    parsed_result = models.JSONField(verbose_name='解析结果')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    def __str__(self):
        return f"{self.user.username}的视频解析记录 - {self.created_at}"
    
    class Meta:
        verbose_name = '视频解析记录'
        verbose_name_plural = '视频解析记录'
        ordering = ['-created_at']
