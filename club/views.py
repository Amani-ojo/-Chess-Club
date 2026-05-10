from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ai_pipeline.models import Game
from ai_pipeline.tasks import fetch_lichess_games_task

from .forms import ContactForm, MemberProfileForm, RegisterForm, UserProfileForm
from .member_utils import sync_member_with_user
from .models import Announcement, Match, Member, Team, TeamMembership, UserProfile
from .queries import members_for_leaderboard
from .services.dashboard_metrics import build_dashboard_metrics, member_games_for_player


def home(request):
    now = timezone.now()
    top_players = Member.objects.order_by('-elo_rating', '-wins')[:5]
    upcoming_matches = Match.objects.filter(status=Match.STATUS_SCHEDULED).select_related(
        'white_player', 'black_player'
    ).order_by('scheduled_at')[:8]
    announcements = Announcement.objects.filter(published_at__lte=now).select_related('author').order_by(
        '-published_at'
    )[:6]
    recent_members = Member.objects.order_by('-pk')[:12]
    recent_games = Game.objects.select_related('player_white', 'player_black')[:8]
    home_stats = {
        'member_total': Member.objects.count(),
        'upcoming_total': Match.objects.filter(status=Match.STATUS_SCHEDULED).count(),
        'announcement_total': Announcement.objects.filter(published_at__lte=now).count(),
    }
    return render(
        request,
        'club/home.html',
        {
            'top_players': top_players,
            'upcoming_matches': upcoming_matches,
            'announcements': announcements,
            'recent_members': recent_members,
            'recent_games': recent_games,
            'home_stats': home_stats,
        },
    )


def member_detail(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    games = member_games_for_player(member)[:20]
    club_matches = (
        Match.objects.filter(Q(white_player=member) | Q(black_player=member))
        .select_related('white_player', 'black_player')
        .order_by('-scheduled_at')[:20]
    )
    elo_hist = member.elo_history.select_related('match').order_by('-created_at')[:25]
    return render(
        request,
        'club/member_detail.html',
        {
            'member': member,
            'games': games,
            'club_matches': club_matches,
            'elo_hist': elo_hist,
        },
    )


@login_required
def member_profile_edit_view(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    if member.user_id != request.user.id:
        messages.error(request, 'You can only edit your own profile.')
        return redirect('club:member_detail', member_id=member.id)
    if request.method == 'POST':
        form = MemberProfileForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('club:member_detail', member_id=member.id)
    else:
        form = MemberProfileForm(instance=member)
    return render(request, 'club/member_profile_edit.html', {'form': form, 'member': member})


def leaderboard_view(request):
    sort = request.GET.get('sort', 'elo')
    if sort not in ('elo', 'winpct'):
        sort = 'elo'
    members = members_for_leaderboard(sort)
    return render(request, 'club/leaderboard.html', {'members': members, 'sort': sort})


def matches_view(request):
    tab = request.GET.get('tab', 'upcoming')
    if tab not in ('upcoming', 'completed'):
        tab = 'upcoming'
    upcoming = Match.objects.filter(status=Match.STATUS_SCHEDULED).order_by('scheduled_at')
    completed = Match.objects.filter(status=Match.STATUS_COMPLETED).order_by('-completed_at', '-scheduled_at')
    return render(
        request,
        'club/matches.html',
        {'tab': tab, 'upcoming': upcoming, 'completed': completed},
    )


def match_detail_view(request, match_id):
    match = get_object_or_404(Match.objects.select_related('white_player', 'black_player'), pk=match_id)
    return render(request, 'club/match_detail.html', {'match': match})


def teams_list_view(request):
    teams = Team.objects.prefetch_related(
        Prefetch('teammembership_set', queryset=TeamMembership.objects.select_related('member'))
    ).all()
    return render(request, 'club/teams_list.html', {'teams': teams})


def team_detail_view(request, slug):
    team = get_object_or_404(
        Team.objects.prefetch_related(
            Prefetch('teammembership_set', queryset=TeamMembership.objects.select_related('member'))
        ),
        slug=slug,
    )
    return render(request, 'club/team_detail.html', {'team': team})


def about_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thanks — we received your message.')
            return redirect('club:about')
    else:
        form = ContactForm()
    return render(request, 'club/about.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('club:dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user)
            sync_member_with_user(user, '')
            login(request, user)
            return redirect('club:dashboard')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def dashboard_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    form = UserProfileForm(request.POST or None, instance=profile)
    auto_sync_queued = False

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_profile' and form.is_valid():
            saved_profile = form.save()
            sync_member_with_user(request.user, saved_profile.lichess_username)
            messages.success(request, 'Lichess profile settings saved.')
            return redirect('club:dashboard')

        if action == 'import_games':
            if not profile.lichess_username:
                messages.error(request, 'Set your Lichess username before importing games.')
                return redirect('club:dashboard')
            member = sync_member_with_user(request.user, profile.lichess_username)
            fetch_lichess_games_task.delay(profile.lichess_username, member.id, profile.lichess_api_key)
            messages.success(request, 'Game import started. Refresh shortly to see imported games.')
            return redirect('club:dashboard')

    games = []
    if profile.lichess_username:
        member = sync_member_with_user(request.user, profile.lichess_username)

        if profile.lichess_api_key:
            now = timezone.now()
            cooldown = timedelta(minutes=5)
            if (
                profile.last_lichess_sync_requested_at is None
                or now - profile.last_lichess_sync_requested_at >= cooldown
            ):
                fetch_lichess_games_task.delay(profile.lichess_username, member.id, profile.lichess_api_key)
                profile.last_lichess_sync_requested_at = now
                profile.save(update_fields=['last_lichess_sync_requested_at'])
                auto_sync_queued = True

        games = member_games_for_player(member)[:20]

    metrics = build_dashboard_metrics(request.user, profile)
    return render(
        request,
        'club/dashboard.html',
        {
            'form': form,
            'profile': profile,
            'games': games,
            'auto_sync_queued': auto_sync_queued,
            'metrics': metrics,
        },
    )


@login_required
def dashboard_metrics_api(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return JsonResponse(build_dashboard_metrics(request.user, profile))
