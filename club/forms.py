from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('lichess_username', 'lichess_api_key', 'theme_preference')
        widgets = {
            'lichess_api_key': forms.PasswordInput(render_value=True, attrs={'placeholder': 'Paste your Lichess API token'}),
            'lichess_username': forms.TextInput(attrs={'placeholder': 'your_lichess_username'}),
            'theme_preference': forms.Select(attrs={'class': 'form-select'}),
        }
