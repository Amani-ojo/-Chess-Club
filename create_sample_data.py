"""
Sample data script for the Eschen Chess Club.

Run from the project root:
    python create_sample_data.py

This creates:
  - 10 club members with Django user accounts
  - 15 matches (mix of completed, scheduled, in progress)
  - ELO history records for completed matches
  - 5 announcements
"""

import os
import sys
import django
from datetime import date, timedelta

# Setup Django before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chess_club.settings')

# Add the project root to the path so Django can find the apps
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from club.models import Member, Match, EloHistory, Announcement


def create_members():
    """Create 10 club members with linked Django user accounts."""

    members_data = [
        {'username': 'lukas',    'display_name': 'Lukas Fehr',       'elo': 1850, 'wins': 42, 'losses': 18, 'draws': 10},
        {'username': 'anna',     'display_name': 'Anna Büchel',      'elo': 1720, 'wins': 35, 'losses': 22, 'draws': 8},
        {'username': 'marco',    'display_name': 'Marco Ospelt',     'elo': 1650, 'wins': 28, 'losses': 25, 'draws': 12},
        {'username': 'elena',    'display_name': 'Elena Hasler',     'elo': 1580, 'wins': 20, 'losses': 20, 'draws': 15},
        {'username': 'noah',     'display_name': 'Noah Wanger',      'elo': 1510, 'wins': 18, 'losses': 22, 'draws': 5},
        {'username': 'sophie',   'display_name': 'Sophie Marxer',    'elo': 1480, 'wins': 15, 'losses': 25, 'draws': 6},
        {'username': 'david',    'display_name': 'David Ritter',     'elo': 1420, 'wins': 12, 'losses': 28, 'draws': 8},
        {'username': 'lena',     'display_name': 'Lena Vogt',        'elo': 1350, 'wins': 10, 'losses': 30, 'draws': 4},
        {'username': 'jan',      'display_name': 'Jan Brunhart',     'elo': 1280, 'wins': 8,  'losses': 32, 'draws': 3},
        {'username': 'mia',      'display_name': 'Mia Kaufmann',     'elo': 1200, 'wins': 5,  'losses': 20, 'draws': 2},
    ]

    created_members = []

    for data in members_data:
        user, _ = User.objects.get_or_create(
            username=data['username'],
            defaults={
                'first_name': data['display_name'].split()[0],
                'last_name': data['display_name'].split()[-1],
                'email': f"{data['username']}@eschenchess.li",
            },
        )
        user.set_password('chess1234')
        user.save()

        member, created = Member.objects.get_or_create(
            user=user,
            defaults={
                'display_name': data['display_name'],
                'elo_rating': data['elo'],
                'wins': data['wins'],
                'losses': data['losses'],
                'draws': data['draws'],
                'joined_date': date(2024, 1, 1) + timedelta(days=members_data.index(data) * 15),
            },
        )

        status = "Created" if created else "Already exists"
        print(f"  {status}: {member.display_name} (ELO {member.elo_rating})")
        created_members.append(member)

    return created_members


def create_matches(members):
    """Create a mix of completed, scheduled, and in-progress matches."""

    now = timezone.now()
    matches_data = [
        # Completed matches
        {'white': 0, 'black': 1, 'status': 'completed', 'result': 'white_wins', 'days_ago': 30, 'venue': 'Eschen Clubhouse'},
        {'white': 2, 'black': 3, 'status': 'completed', 'result': 'draw',       'days_ago': 28, 'venue': 'Eschen Clubhouse'},
        {'white': 4, 'black': 5, 'status': 'completed', 'result': 'black_wins', 'days_ago': 25, 'venue': 'Vaduz Library'},
        {'white': 1, 'black': 6, 'status': 'completed', 'result': 'white_wins', 'days_ago': 22, 'venue': 'Eschen Clubhouse'},
        {'white': 0, 'black': 2, 'status': 'completed', 'result': 'white_wins', 'days_ago': 20, 'venue': 'Online (Lichess)'},
        {'white': 3, 'black': 7, 'status': 'completed', 'result': 'white_wins', 'days_ago': 18, 'venue': 'Eschen Clubhouse'},
        {'white': 8, 'black': 9, 'status': 'completed', 'result': 'draw',       'days_ago': 15, 'venue': 'Schaan Community Centre'},
        {'white': 5, 'black': 0, 'status': 'completed', 'result': 'black_wins', 'days_ago': 12, 'venue': 'Eschen Clubhouse'},
        {'white': 1, 'black': 3, 'status': 'completed', 'result': 'white_wins', 'days_ago': 10, 'venue': 'Online (Lichess)'},
        {'white': 6, 'black': 4, 'status': 'completed', 'result': 'draw',       'days_ago': 7,  'venue': 'Eschen Clubhouse'},
        # In-progress matches
        {'white': 0, 'black': 3, 'status': 'in_progress', 'result': None, 'days_ago': 0, 'venue': 'Eschen Clubhouse'},
        # Scheduled (future) matches
        {'white': 2, 'black': 5, 'status': 'scheduled', 'result': None, 'days_ago': -3,  'venue': 'Eschen Clubhouse'},
        {'white': 1, 'black': 4, 'status': 'scheduled', 'result': None, 'days_ago': -7,  'venue': 'Vaduz Library'},
        {'white': 7, 'black': 9, 'status': 'scheduled', 'result': None, 'days_ago': -10, 'venue': 'Online (Lichess)'},
        {'white': 0, 'black': 8, 'status': 'scheduled', 'result': None, 'days_ago': -14, 'venue': 'Eschen Clubhouse'},
    ]

    created_matches = []

    for i, data in enumerate(matches_data):
        match, created = Match.objects.get_or_create(
            player_white=members[data['white']],
            player_black=members[data['black']],
            scheduled_at=now - timedelta(days=data['days_ago']),
            defaults={
                'venue': data['venue'],
                'round_number': i + 1,
                'status': data['status'],
                'result': data['result'],
            },
        )
        status = "Created" if created else "Already exists"
        print(f"  {status}: {match}")
        created_matches.append(match)

    return created_matches


def create_elo_history(members, matches):
    """Create ELO history records for completed matches."""

    completed = [m for m in matches if m.status == 'completed']

    for match in completed:
        white = match.player_white
        black = match.player_black

        # Simple ELO change simulation
        if match.result == 'white_wins':
            white_change = 12
            black_change = -12
        elif match.result == 'black_wins':
            white_change = -12
            black_change = 12
        else:
            white_change = 0
            black_change = 0

        _, created_w = EloHistory.objects.get_or_create(
            member=white,
            match=match,
            defaults={
                'rating_before': white.elo_rating - white_change,
                'rating_after': white.elo_rating,
            },
        )

        _, created_b = EloHistory.objects.get_or_create(
            member=black,
            match=match,
            defaults={
                'rating_before': black.elo_rating - black_change,
                'rating_after': black.elo_rating,
            },
        )

        if created_w or created_b:
            print(f"  ELO history: {match}")


def create_announcements():
    """Create 5 club announcements."""

    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.first()

    now = timezone.now()

    announcements_data = [
        {
            'title': 'Welcome to the Eschen Chess Club Website!',
            'body': 'We are excited to launch our new website. Here you can track your ELO rating, view upcoming matches, and stay up to date with club news. Register your account to get started!',
            'days_ago': 60,
            'is_published': True,
        },
        {
            'title': 'Spring Tournament 2026 — Registration Open',
            'body': 'Our annual Spring Tournament is coming up on April 19th. All club members are welcome to participate. Register by April 12th to secure your spot. Format: Swiss system, 7 rounds, 15+10 time control.',
            'days_ago': 14,
            'is_published': True,
        },
        {
            'title': 'New Club Hours Starting April',
            'body': 'Starting April 1st, the clubhouse will be open on Tuesdays and Thursdays from 18:00 to 21:00, and Saturdays from 14:00 to 18:00. See you there!',
            'days_ago': 10,
            'is_published': True,
        },
        {
            'title': 'Lichess Team Created',
            'body': 'We now have an official Lichess team! Join "Eschen Chess Club" on lichess.org to play rated games against fellow members online. Weekly online blitz arena every Wednesday at 20:00.',
            'days_ago': 5,
            'is_published': True,
        },
        {
            'title': 'Beginner Workshop — Learn the Basics',
            'body': 'Interested in chess but not sure where to start? Join our free beginner workshop on April 26th at 14:00 in the clubhouse. We will cover the rules, basic openings, and simple tactics. Bring a friend!',
            'days_ago': 2,
            'is_published': True,
        },
    ]

    for data in announcements_data:
        announcement, created = Announcement.objects.get_or_create(
            title=data['title'],
            defaults={
                'body': data['body'],
                'published_at': now - timedelta(days=data['days_ago']),
                'is_published': data['is_published'],
                'author': admin_user,
            },
        )
        status = "Created" if created else "Already exists"
        print(f"  {status}: {announcement.title}")


def main():
    print("\n=== Creating Sample Data for Eschen Chess Club ===\n")

    print("Members:")
    members = create_members()

    print("\nMatches:")
    matches = create_matches(members)

    print("\nELO History:")
    create_elo_history(members, matches)

    print("\nAnnouncements:")
    create_announcements()

    print("\n=== Done! Sample data created successfully. ===")
    print(f"    Members: {Member.objects.count()}")
    print(f"    Matches: {Match.objects.count()}")
    print(f"    ELO History records: {EloHistory.objects.count()}")
    print(f"    Announcements: {Announcement.objects.count()}")
    print()


if __name__ == '__main__':
    main()
