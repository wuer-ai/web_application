from django.shortcuts import render, redirect, get_object_or_404
import json
import requests
from datetime import date
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
from django.views.decorators.http import require_POST
import yt_dlp
import os
import tempfile

from .forms import RegisterForm, VideoParsingForm
from .models import UserProfile, VideoParsingRecord

def index(request):
    form = VideoParsingForm()
    return render(request, 'video_parser/index.html', {'form': form})

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # 用户注册自动创建资料并设置初始积分在signals中完成
            login(request, user)
            messages.success(request, '注册成功！已赠送您10积分。')
            return redirect('index')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})

def check_login_reward(request):
    """检查并发放每日首次登录奖励"""
    if request.user.is_authenticated:
        profile = request.user.profile
        today = date.today()
        
        # 如果今天还没有领取奖励
        if not profile.last_login_reward_date or profile.last_login_reward_date < today:
            profile.points += 10
            profile.last_login_reward_date = today
            profile.save()
            messages.success(request, '每日登录奖励：+10积分')
            return True
    return False

@login_required
def parse_video(request):
    if request.method == 'POST':
        form = VideoParsingForm(request.POST)
        if form.is_valid():
            # 检查用户积分是否足够
            profile = request.user.profile
            if profile.points < 1:
                messages.error(request, '积分不足，无法解析视频。')
                return redirect('index')
            
            # 调用Coze API解析视频
            video_url = form.cleaned_data['video_url']
            api_url = 'https://api.coze.cn/v1/workflow/run'
            headers = {
                'Authorization': f'Bearer {settings.COZE_API_KEY}',
                'Content-Type': 'application/json'
            }
            payload = {
                'parameters': {
                    'input': video_url
                },
                'workflow_id': settings.COZE_WORKFLOW_ID
            }
            
            try:
                response = requests.post(api_url, headers=headers, json=payload)
                response_data = response.json()
                
                if response_data.get('code') == 0:
                    # 扣除积分
                    profile.points -= 1
                    profile.save()
                    
                    # 提取解析结果
                    result_json = json.loads(response_data.get('data', '{}'))
                    
                    # 保存解析记录
                    record = VideoParsingRecord.objects.create(
                        user=request.user,
                        video_url=video_url,
                        parsed_result=result_json
                    )
                    
                    # 返回解析结果
                    return render(request, 'video_parser/result.html', {
                        'result': result_json.get('output', {}),
                        'video_url': video_url,
                        'record': record
                    })
                else:
                    messages.error(request, f'解析失败：{response_data.get("msg", "未知错误")}')
            except Exception as e:
                messages.error(request, f'解析过程出错：{str(e)}')
        else:
            messages.error(request, '请输入有效的视频链接')
    
    return redirect('index')

@login_required
def download_video(request, record_id):
    """处理视频播放请求 - 不再直接下载，而是通过安全的播放页面处理"""
    record = get_object_or_404(VideoParsingRecord, id=record_id, user=request.user)
    result = record.parsed_result.get('output', {})
    
    # 获取视频标题
    title = result.get('title', '视频播放')
    
    # 确定视频URL
    video_url = None
    
    # 对于Coze API返回的视频，直接使用其视频链接
    if result.get('video'):
        video_url = result.get('video')
        # 传递视频URL到嵌入式播放器页面
        return render(request, 'video_parser/embedded_player.html', {
            'video_url': video_url,
            'title': title,
            'record': record
        })
    
    # 对于YouTube视频，尝试使用yt-dlp获取链接
    if 'youtube.com' in record.video_url or 'youtu.be' in record.video_url:
        try:
            # 配置yt-dlp选项
            ydl_opts = {
                'format': 'best[ext=mp4]',
                'cookiesfrombrowser': ('chrome', 'firefox'),
                'quiet': True,
                'nocheckcertificate': True,
                'ignoreerrors': True,
                'no_warnings': True,
                'noplaylist': True,
                'geo_bypass': True,
                'geo_bypass_country': 'US',
                'extractor_retries': 10,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'referer': 'https://www.youtube.com/',
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'web'],
                        'hl': ['en-US'],
                        'iv_load_policy': ['1'],
                    }
                },
            }
            
            # 尝试获取视频信息
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(record.video_url, download=False)
                
                # 如果成功获取信息
                if info:
                    # 优先获取普通的mp4格式，而不是dash格式
                    formats = info.get('formats', [])
                    for fmt in formats:
                        if fmt.get('ext') == 'mp4' and fmt.get('acodec') != 'none' and fmt.get('vcodec') != 'none':
                            video_url = fmt.get('url')
                            break
                    
                    # 如果没有找到合适的格式，使用yt-dlp选择的最佳格式
                    if not video_url and 'url' in info:
                        video_url = info['url']
                    
                    # 获取更准确的标题
                    if info.get('title'):
                        title = info['title']
        except Exception as e:
            print(f"yt-dlp获取失败: {str(e)}")
            # 不向用户显示技术错误，继续处理
    
    # 如果一切尝试都失败，但我们有原始链接
    if not video_url:
        # 提供更友好的错误信息
        messages.warning(request, '无法获取视频播放链接，请尝试访问原始网站。')
        return redirect('index')
    
    # 返回嵌入式播放器页面
    return render(request, 'video_parser/embedded_player.html', {
        'video_url': video_url,
        'title': title,
        'record': record
    })

@login_required
def user_profile(request):
    """显示用户个人资料和积分信息"""
    # 调用检查并发放每日登录奖励的函数
    check_login_reward(request)
    
    # 获取用户的解析记录
    records = VideoParsingRecord.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    return render(request, 'video_parser/profile.html', {
        'profile': request.user.profile,
        'records': records
    })
