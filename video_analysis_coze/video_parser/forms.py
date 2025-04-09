from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label='电子邮箱')
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        
    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        self.fields['username'].label = '用户名'
        self.fields['password1'].label = '密码'
        self.fields['password2'].label = '确认密码'
        
class VideoParsingForm(forms.Form):
    video_url = forms.URLField(
        label='视频链接',
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': '请输入视频链接'}),
        required=True
    ) 