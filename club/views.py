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
    # Get top 5 players sorted by ELO rating (highest first)
    top_players = Member.objects.filter(is_active=True).order_by('-elo_rating')[:5]

    # Get next 3 upcoming matches (scheduled in the future)
    upcoming_matches = Match.objects.filter(
        status='scheduled',
        scheduled_at__gte=timezone.now()
    ).order_by('scheduled_at')[:3]

    # Get latest published announcements
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

    # Get all active members
    members = Member.objects.filter(is_active=True)

    # Sort by the chosen field
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

    # Get upcoming matches (scheduled or in progress, in the future)
    upcoming = Match.objects.filter(
        status__in=['scheduled', 'in_progress'],
        scheduled_at__gte=timezone.now()
    ).order_by('scheduled_at')

    # Get completed match results
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

    # Get ELO history for the chart
    elo_history = EloHistory.objects.filter(member=member).order_by('recorded_at')

    # Get recent matches (last 20) where this member played
    from django.db.models import Q
    recent_matches = Match.objects.filter(
        Q(player_white=member) | Q(player_black=member),
        status='completed'
    ).order_by('-scheduled_at')[:20]

    # Prepare ELO chart data
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
            # In production this would send an email
            # For now, just show a success message
            messages.success(request, 'Your message has been sent! We will get back to you soon.')
            form = ContactForm()
    else:
        form = ContactForm()

    context = {
        'form': form,
    }
    return render(request, 'club/about.html', context)
