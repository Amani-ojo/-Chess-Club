import base64
import io
from datetime import timedelta
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
import django_otp
from django_otp.plugins.otp_totp.models import TOTPDevice
import qrcode

from ai_pipeline.models import Game
from ai_pipeline.tasks import fetch_lichess_games_task

from .constants import CLUB_PRIMARY_VENUE
from .forms import ContactForm, MemberProfileForm, UserProfileForm
from .member_utils import sync_member_with_user
from .models import (
    Announcement,
    Match,
    Member,
    SwissTournament,
    Team,
    TeamMembership,
    UserProfile,
)
from .otp_gate import otp_session_redirect_if_needed, otp_verified_safe, resolve_safe_next
from .queries import members_for_leaderboard
from .services.dashboard_metrics import build_dashboard_metrics, member_games_for_player
from .services.swiss_pairing import tournament_standings_rows


class ClubLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if getattr(user, 'is_authenticated', False) and not otp_verified_safe(user):
            cand = self.request.POST.get(self.redirect_field_name) or self.request.GET.get(self.redirect_field_name)
            fb = reverse('club:dashboard')
            safe = resolve_safe_next(self.request, cand if cand else fb)
            return reverse('club:otp_verify') + '?next=' + quote(safe, safe='/')
        return super().get_success_url()


def _otp_qr_data_uri(config_url: str) -> str:
    img = qrcode.make(config_url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


@login_required
@require_http_methods(['GET', 'POST'])
def otp_verify_view(request):
    devices = list(TOTPDevice.objects.filter(user=request.user, confirmed=True))
    if not devices:
        return redirect(reverse('club:dashboard'))
    if otp_verified_safe(request.user):
        return redirect(resolve_safe_next(request, request.GET.get('next')))

    next_path = resolve_safe_next(request, request.GET.get('next'))

    if request.method == 'POST':
        token = request.POST.get('otp_token', '').replace(' ', '')
        for device in devices:
            if device.verify_token(token):
                django_otp.login(request, device)
                raw = request.POST.get('next') or ''
                return redirect(resolve_safe_next(request, raw if raw else next_path))
        messages.error(request, 'Invalid authenticator code.')

    return render(
        request,
        'registration/otp_verify.html',
        {'next_path': next_path},
    )


@login_required
@require_http_methods(['GET', 'POST'])
def totp_manage_view(request):
    if request.method == 'POST':
        confirmed = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
        pending = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
        if 'disable' in request.POST and confirmed:
            TOTPDevice.objects.filter(user=request.user).delete()
            messages.success(request, 'Two-factor authentication is now off for your account.')
            return redirect('club:dashboard')
        if 'start' in request.POST and not confirmed and not pending:
            TOTPDevice.objects.create(user=request.user, name='default')
            return redirect('club:totp_manage')
        if 'confirm' in request.POST and pending:
            tok = request.POST.get('otp_token', '').replace(' ', '')
            if pending.verify_token(tok):
                pending.confirmed = True
                pending.save()
                django_otp.login(request, pending)
                messages.success(request, 'Authenticator enabled.')
                return redirect('club:dashboard')
            messages.error(request, 'Code did not match. Try scanning the QR again.')

    pending = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
    confirmed = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
    qr_data_uri = None
    config_url = None
    if pending:
        config_url = pending.config_url
        qr_data_uri = _otp_qr_data_uri(config_url)

    return render(
        request,
        'club/totp_manage.html',
        {
            'confirmed_device': confirmed,
            'pending_device': pending,
            'config_url': config_url,
            'qr_data_uri': qr_data_uri,
        },
    )


def tournament_list_view(request):
    qs = SwissTournament.objects.all()
    return render(request, 'club/tournament_list.html', {'tournaments': qs})


def tournament_detail_view(request, slug):
    tournament = get_object_or_404(SwissTournament, slug=slug)
    rounds = tournament.rounds.prefetch_related('pairings__white', 'pairings__black').all()
    standings = tournament_standings_rows(tournament)
    return render(
        request,
        'club/tournament_detail.html',
        {
            'tournament': tournament,
            'rounds': rounds,
            'standings': standings,
        },
    )


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
    redir = otp_session_redirect_if_needed(request)
    if redir:
        return redir
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
    return render(
        request,
        'club/about.html',
        {'form': form, 'club_primary_venue': CLUB_PRIMARY_VENUE},
    )


def register_view(request):
    if request.user.is_authenticated:
        return redirect('club:dashboard')
    return render(request, 'registration/register.html', {})


@login_required
def dashboard_view(request):
    redir = otp_session_redirect_if_needed(request)
    if redir:
        return redir
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
    redir = otp_session_redirect_if_needed(request)
    if redir:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'detail': 'authenticator_challenge_required'}, status=401)
        return redir
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return JsonResponse(build_dashboard_metrics(request.user, profile))
=======
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from .models import Member, Match, Announcement, EloHistory
from .forms import ContactForm


def home(request):
    """
    Home page view.
    Shows welcome message, top 5 players, next 3 upcoming matches,
    and latest published announcements.
    """
    top_players = Member.objects.filter(is_active=True).order_by('-elo_rating')[:5]

    upcoming_matches = Match.objects.filter(
        status='scheduled',
        scheduled_at__gte=timezone.now()
    ).order_by('scheduled_at')[:3]

    announcements = Announcement.objects.filter(
        is_published=True,
        published_at__lte=timezone.now()
    )[:3]

    context = {
        'top_players': top_players,
        'upcoming_matches': upcoming_matches,
        'announcements': announcements,
    }
    return render(request, 'club/home.html', context)


def leaderboard(request):
    """
    Leaderboard page view.
    Displays all active members ranked by ELO rating.
    Supports toggling sort between ELO and Win %.
    """
    sort_by = request.GET.get('sort', 'elo')

    members = Member.objects.filter(is_active=True)

    if sort_by == 'wins':
        members = sorted(members, key=lambda m: m.win_percentage(), reverse=True)
    else:
        members = members.order_by('-elo_rating')

    context = {
        'members': members,
        'sort_by': sort_by,
    }
    return render(request, 'club/leaderboard.html', context)


def matches(request):
    """
    Matches page view.
    Shows upcoming matches and completed results in a tabbed layout.
    """
    tab = request.GET.get('tab', 'upcoming')

    upcoming = Match.objects.filter(
        status__in=['scheduled', 'in_progress'],
        scheduled_at__gte=timezone.now()
    ).order_by('scheduled_at')

    results = Match.objects.filter(
        status='completed'
    ).order_by('-scheduled_at')

    context = {
        'upcoming': upcoming,
        'results': results,
        'tab': tab,
    }
    return render(request, 'club/matches.html', context)


def match_detail(request, pk):
    """
    Match detail page view.
    Shows full details of a single match.
    """
    match = get_object_or_404(Match, pk=pk)

    context = {
        'match': match,
    }
    return render(request, 'club/match_detail.html', context)


def member_profile(request, pk):
    """
    Member profile page view.
    Displays member stats, ELO history, and recent match history.
    """
    member = get_object_or_404(Member, pk=pk)

    elo_history = EloHistory.objects.filter(member=member).order_by('recorded_at')

    from django.db.models import Q
    recent_matches = Match.objects.filter(
        Q(player_white=member) | Q(player_black=member),
        status='completed'
    ).order_by('-scheduled_at')[:20]

    elo_dates = [h.recorded_at.strftime('%d %b %Y') for h in elo_history]
    elo_values = [h.rating_after for h in elo_history]

    context = {
        'member': member,
        'elo_history': elo_history,
        'recent_matches': recent_matches,
        'elo_dates': elo_dates,
        'elo_values': elo_values,
    }
    return render(request, 'club/member_profile.html', context)


def about(request):
    """
    About page view.
    Shows club info and a contact form.
    """
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            messages.success(request, 'Your message has been sent! We will get back to you soon.')
            form = ContactForm()
    else:
        form = ContactForm()

    context = {
        'form': form,
    }
    return render(request, 'club/about.html', context)

