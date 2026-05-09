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

    class Meta:
        model = User
        fields = ('username', 'display_name', 'email', 'password1', 'password2')

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
            )
        return user


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
