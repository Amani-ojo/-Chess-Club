from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .models import Member


class RegisterForm(UserCreationForm):
    """
    Registration form for new club members.
    Creates a Django User and a linked Member profile in one step.
    Optionally captures Lichess credentials so the AI pipeline can
    fetch and analyse the member's online games.
    """
    display_name = forms.CharField(
        max_length=100,
        required=True,
        label='Display name',
        help_text='How your name will appear on the leaderboard.',
    )
    email = forms.EmailField(
        required=True,
        help_text='We use this only for club communication.',
    )
    lichess_username = forms.CharField(
        max_length=30,
        required=False,
        label='Lichess username (optional)',
        help_text='If you play on lichess.org, share your username so we can analyse your games.',
    )
    lichess_token = forms.CharField(
        max_length=255,
        required=False,
        label='Lichess API token (optional)',
        widget=forms.PasswordInput(render_value=False),
        help_text='Generate one at lichess.org/account/oauth/token. '
                  'Only needed for higher rate limits or private studies. Leave blank if unsure.',
    )

    class Meta:
        model = User
        fields = ('username', 'display_name', 'email', 'password1', 'password2',
                  'lichess_username', 'lichess_token')

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            Member.objects.create(
                user=user,
                display_name=self.cleaned_data['display_name'],
                joined_date=timezone.now().date(),
                lichess_username=self.cleaned_data.get('lichess_username', '').strip(),
                lichess_token=self.cleaned_data.get('lichess_token', '').strip(),
            )
        return user


class ProfileEditForm(forms.ModelForm):
    """
    Lets members update their display name, avatar, and Lichess credentials.
    """
    lichess_token = forms.CharField(
        max_length=255,
        required=False,
        label='Lichess API token',
        widget=forms.PasswordInput(render_value=False),
        help_text='Leave blank to keep your existing token. Generate a new one at '
                  'lichess.org/account/oauth/token.',
    )

    class Meta:
        model = Member
        fields = ('display_name', 'avatar', 'lichess_username', 'lichess_token')
        help_texts = {
            'lichess_username': 'Your public Lichess username — used by the AI pipeline to fetch your games.',
        }

    def save(self, commit=True):
        # Don't overwrite an existing token with an empty submission.
        new_token = self.cleaned_data.get('lichess_token', '').strip()
        if not new_token and self.instance.pk:
            self.instance.lichess_token = Member.objects.get(pk=self.instance.pk).lichess_token
        else:
            self.instance.lichess_token = new_token
        return super().save(commit=commit)


class ContactForm(forms.Form):
    """
    Contact form displayed on the About page.
    Allows visitors to send a message to the club administrators.
    """
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your full name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Write your message here...',
            'rows': 5
        })
    )
