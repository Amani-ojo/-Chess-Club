from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ai_pipeline.models import Game, GameAnalysis, MoveEvaluation
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
    auto_sync_queued = False
    member = None

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
        member, _ = Member.objects.get_or_create(
            display_name=request.user.username,
            defaults={'lichess_username': profile.lichess_username},
        )
        if member.lichess_username != profile.lichess_username:
            member.lichess_username = profile.lichess_username
            member.save(update_fields=['lichess_username'])

        # Auto-sync dashboard games with a short cooldown to prevent task spam.
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

        if member:
            games = (
                Game.objects.filter(player_white=member) | Game.objects.filter(player_black=member)
            ).select_related('player_white', 'player_black').distinct()[:20]
    metrics = _build_dashboard_metrics(profile)
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


def _build_elo_history_for_member(member):
    all_games = Game.objects.select_related('player_white', 'player_black').order_by('played_at', 'id')
    ratings = {}
    history = []
    k_factor = 20

    for game in all_games:
        white_id = game.player_white_id
        black_id = game.player_black_id
        white_rating = ratings.get(white_id, 1200.0)
        black_rating = ratings.get(black_id, 1200.0)

        expected_white = 1.0 / (1.0 + (10 ** ((black_rating - white_rating) / 400.0)))
        expected_black = 1.0 - expected_white

        if game.result == '1-0':
            score_white, score_black = 1.0, 0.0
        elif game.result == '0-1':
            score_white, score_black = 0.0, 1.0
        else:
            score_white, score_black = 0.5, 0.5

        white_new = white_rating + k_factor * (score_white - expected_white)
        black_new = black_rating + k_factor * (score_black - expected_black)
        ratings[white_id] = white_new
        ratings[black_id] = black_new

        if member and (game.player_white_id == member.id or game.player_black_id == member.id):
            history.append(
                {
                    'x': game.played_at.strftime('%Y-%m-%d'),
                    'y': round(ratings[member.id], 2),
                }
            )
    return history


def _build_skill_radar(member):
    if not member:
        return {
            'labels': ['Opening Accuracy', 'Middlegame Accuracy', 'Endgame Accuracy', 'Tactical Safety'],
            'values': [0, 0, 0, 0],
        }

    analyses = (
        GameAnalysis.objects.filter(status='completed')
        .filter(game__player_white=member) | GameAnalysis.objects.filter(status='completed').filter(game__player_black=member)
    ).distinct().select_related('game')

    opening, middlegame, endgame = [], [], []
    tactical_penalty = 0

    for analysis in analyses:
        is_white = analysis.game.player_white_id == member.id
        evals = MoveEvaluation.objects.filter(analysis=analysis, is_white=is_white)
        for ev in evals:
            if ev.move_number <= 15:
                opening.append(ev.centipawn_loss)
            elif ev.move_number <= 35:
                middlegame.append(ev.centipawn_loss)
            else:
                endgame.append(ev.centipawn_loss)
            if ev.classification in ('mistake', 'blunder'):
                tactical_penalty += 1

    def accuracy(cpls):
        if not cpls:
            return 0
        avg_cpl = sum(cpls) / len(cpls)
        return max(0, min(100, round(100 - (avg_cpl * 0.9), 2)))

    tactical_safety = max(0, min(100, round(100 - tactical_penalty * 2.5, 2)))
    return {
        'labels': ['Opening Accuracy', 'Middlegame Accuracy', 'Endgame Accuracy', 'Tactical Safety'],
        'values': [accuracy(opening), accuracy(middlegame), accuracy(endgame), tactical_safety],
    }


def _build_standings():
    games = Game.objects.select_related('player_white', 'player_black').order_by('played_at')
    standings = {}

    def ensure(member):
        if member.id not in standings:
            standings[member.id] = {
                'member_id': member.id,
                'name': member.display_name,
                'points': 0.0,
                'wins': 0,
                'draws': 0,
                'losses': 0,
                'played': 0,
                'opponents': set(),
            }
        return standings[member.id]

    for game in games:
        white = ensure(game.player_white)
        black = ensure(game.player_black)
        white['played'] += 1
        black['played'] += 1
        white['opponents'].add(game.player_black_id)
        black['opponents'].add(game.player_white_id)

        if game.result == '1-0':
            white['points'] += 1.0
            white['wins'] += 1
            black['losses'] += 1
        elif game.result == '0-1':
            black['points'] += 1.0
            black['wins'] += 1
            white['losses'] += 1
        else:
            white['points'] += 0.5
            black['points'] += 0.5
            white['draws'] += 1
            black['draws'] += 1

    for item in standings.values():
        item['buchholz'] = round(sum(standings[opp]['points'] for opp in item['opponents'] if opp in standings), 2)
        item.pop('opponents', None)

    sorted_rows = sorted(standings.values(), key=lambda r: (r['points'], r['buchholz'], r['wins']), reverse=True)
    for idx, row in enumerate(sorted_rows, start=1):
        row['rank'] = idx
    return sorted_rows


def _build_dashboard_metrics(profile):
    member = None
    if profile.lichess_username:
        member = Member.objects.filter(lichess_username=profile.lichess_username).first()
    return {
        'elo_progress': _build_elo_history_for_member(member),
        'skill_radar': _build_skill_radar(member),
        'standings': _build_standings(),
    }


@login_required
def dashboard_metrics_api(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return JsonResponse(_build_dashboard_metrics(profile))
