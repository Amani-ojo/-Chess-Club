from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ai_pipeline.models import Game
from ai_pipeline.tasks import fetch_lichess_games_task

from .forms import RegisterForm, UserProfileForm
from .models import Member, UserProfile


def home(request):
    members = Member.objects.all()[:10]
    recent_games = Game.objects.select_related('player_white', 'player_black')[:10]
    return render(
        request,
        'club/home.html',
        {
            'members': members,
            'recent_games': recent_games,
        },
    )


def member_detail(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    games = Game.objects.filter(player_white=member) | Game.objects.filter(player_black=member)
    games = games.select_related('player_white', 'player_black').distinct()[:20]
    return render(
        request,
        'club/member_detail.html',
        {
            'member': member,
            'games': games,
        },
    )


def register_view(request):
    if request.user.is_authenticated:
        return redirect('club:dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            return redirect('club:dashboard')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def dashboard_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    form = UserProfileForm(request.POST or None, instance=profile)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_profile' and form.is_valid():
            saved_profile = form.save()
            if saved_profile.lichess_username:
                member, _ = Member.objects.get_or_create(
                    display_name=request.user.username,
                    defaults={'lichess_username': saved_profile.lichess_username},
                )
                member.lichess_username = saved_profile.lichess_username
                member.save(update_fields=['lichess_username'])
            messages.success(request, 'Lichess profile settings saved.')
            return redirect('club:dashboard')

        if action == 'import_games':
            if not profile.lichess_username:
                messages.error(request, 'Set your Lichess username before importing games.')
                return redirect('club:dashboard')
            member, _ = Member.objects.get_or_create(
                display_name=request.user.username,
                defaults={'lichess_username': profile.lichess_username},
            )
            fetch_lichess_games_task.delay(profile.lichess_username, member.id, profile.lichess_api_key)
            messages.success(request, 'Game import started. Refresh shortly to see imported games.')
            return redirect('club:dashboard')

    games = []
    if profile.lichess_username:
        member = Member.objects.filter(lichess_username=profile.lichess_username).first()
        if member:
            games = (
                Game.objects.filter(player_white=member) | Game.objects.filter(player_black=member)
            ).select_related('player_white', 'player_black').distinct()[:20]
    return render(request, 'club/dashboard.html', {'form': form, 'profile': profile, 'games': games})
