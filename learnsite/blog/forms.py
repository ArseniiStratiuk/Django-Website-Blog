from django import forms
from .models import Profile, Comment
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from captcha.fields import CaptchaField


class RegisterForm(UserCreationForm):
    email = forms.EmailField(max_length=100, help_text="Обов'язкове поле")
    captcha = CaptchaField()

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class ProfileForm(forms.ModelForm):
    avatar = forms.ImageField(widget=forms.FileInput(attrs={'class': 'form-control-file'}))
    about = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}))

    class Meta:
        model = Profile
        fields = ['avatar', 'about']
        
        
class AddCommentForm(forms.ModelForm):
    content = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'Ваш коментар тут...', 
                                                    'class': 'form-control'}))
    
    class Meta:
        model = Comment
        fields = ['content']