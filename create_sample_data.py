"""
Sample Data Script
==================
Run this script to populate the database with sample chess club data.
Usage: python manage.py shell < create_sample_data.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chess_club.settings')
django.setup()

from django.contrib.auth.models import User
from club.models import Member, Match, Announcement, EloHistory
from django.utils import timezone
from datetime import timedelta

print("Creating sample data...")

# ==================== CREATE ADMIN USER ====================
admin_user, created = User.objects.get_or_create(
    username='admin',
    defaults={'email': 'admin@eschen-chess.li', 'is_staff': True, 'is_superuser': True}
)
if created:
    admin_user.set_password('admin123')
    admin_user.save()
    print("  Created admin user (username: admin, password: admin123)")

# ==================== CREATE MEMBER USERS ====================
member_data = [
    {'username': 'magnus', 'display_name': 'Magnus Eriksson', 'elo': 1850, 'wins': 28, 'losses': 8, 'draws': 6},
    {'username': 'anna', 'display_name': 'Anna Brunner', 'elo': 1720, 'wins': 22, 'losses': 12, 'draws': 8},
    {'username': 'lucas', 'display_name': 'Lucas Fehr', 'elo': 1680, 'wins': 20, 'losses': 14, 'draws': 5},
    {'username': 'sophie', 'display_name': 'Sophie Hasler', 'elo': 1610, 'wins': 18, 'losses': 15, 'draws': 7},
    {'username': 'thomas', 'display_name': 'Thomas Vogt', 'elo': 1550, 'wins': 15, 'losses': 18, 'draws': 4},
    {'username': 'elena', 'display_name': 'Elena Risch', 'elo': 1480, 'wins': 12, 'losses': 20, 'draws': 6},
    {'username': 'marco', 'display_name': 'Marco Ospelt', 'elo': 1420, 'wins': 10, 'losses': 22, 'draws': 3},
    {'username': 'lisa', 'display_name': 'Lisa Wanger', 'elo': 1350, 'wins': 8, 'losses': 24, 'draws': 5},
]

members = []
for i, data in enumerate(member_data):
    user, created = User.objects.get_or_create(
        username=data['username'],
        defaults={'email': f"{data['username']}@eschen-chess.li"}
    )
    if created:
        user.set_password('member123')
        user.save()

    member, created = Member.objects.get_or_create(
        user=user,
        defaults={
            'display_name': data['display_name'],
            'elo_rating': data['elo'],
            'wins': data['wins'],
            'losses': data['losses'],
            'draws': data['draws'],
            'joined_date': timezone.now().date() - timedelta(days=365 - i * 30),
            'is_active': True,
        }
    )
    members.append(member)
    print(f"  Created member: {data['display_name']} (ELO: {data['elo']})")

# ==================== CREATE UPCOMING MATCHES ====================
now = timezone.now()
upcoming_matches = [
    {'white': 0, 'black': 1, 'days': 3, 'venue': 'Main Hall, Table 1', 'round': 1},
    {'white': 2, 'black': 3, 'days': 3, 'venue': 'Main Hall, Table 2', 'round': 1},
    {'white': 4, 'black': 5, 'days': 5, 'venue': 'Main Hall, Table 3', 'round': 2},
    {'white': 6, 'black': 7, 'days': 5, 'venue': 'Main Hall, Table 4', 'round': 2},
    {'white': 0, 'black': 3, 'days': 10, 'venue': 'Tournament Room', 'round': 3},
]

for data in upcoming_matches:
    Match.objects.get_or_create(
        player_white=members[data['white']],
        player_black=members[data['black']],
        scheduled_at=now + timedelta(days=data['days']),
        defaults={
            'venue': data['venue'],
            'round_number': data['round'],
            'status': 'scheduled',
        }
    )
print("  Created 5 upcoming matches")

# ==================== CREATE COMPLETED MATCHES ====================
completed_matches = [
    {'white': 0, 'black': 2, 'days': -5, 'venue': 'Main Hall, Table 1', 'result': 'white_wins'},
    {'white': 1, 'black': 3, 'days': -5, 'venue': 'Main Hall, Table 2', 'result': 'black_wins'},
    {'white': 4, 'black': 6, 'days': -10, 'venue': 'Main Hall, Table 3', 'result': 'draw'},
    {'white': 5, 'black': 7, 'days': -10, 'venue': 'Main Hall, Table 4', 'result': 'white_wins'},
    {'white': 0, 'black': 4, 'days': -15, 'venue': 'Tournament Room', 'result': 'white_wins'},
    {'white': 1, 'black': 5, 'days': -15, 'venue': 'Tournament Room', 'result': 'white_wins'},
    {'white': 2, 'black': 6, 'days': -20, 'venue': 'Main Hall, Table 1', 'result': 'black_wins'},
    {'white': 3, 'black': 7, 'days': -20, 'venue': 'Main Hall, Table 2', 'result': 'white_wins'},
]

for data in completed_matches:
    match, created = Match.objects.get_or_create(
        player_white=members[data['white']],
        player_black=members[data['black']],
        scheduled_at=now + timedelta(days=data['days']),
        defaults={
            'venue': data['venue'],
            'status': 'completed',
            'result': data['result'],
        }
    )
print("  Created 8 completed matches")

# ==================== CREATE ANNOUNCEMENTS ====================
announcements = [
    {
        'title': 'Spring Tournament 2026 Registration Open!',
        'body': 'We are excited to announce our annual Spring Tournament! Registration is now open for all active club members. The tournament will follow a Swiss-system format over 5 rounds. Prizes for the top 3 finishers include trophies and chess book sets. Sign up at the front desk during any club session.',
        'days': -1,
    },
    {
        'title': 'New Club Meeting Room',
        'body': 'Starting next month, we will be meeting in the renovated community hall at Eschen Dorfplatz. The new space features better lighting, more tables, and a dedicated analysis corner with digital boards. We look forward to seeing everyone there!',
        'days': -7,
    },
    {
        'title': 'Congratulations to Magnus Eriksson!',
        'body': 'A huge congratulations to Magnus Eriksson for reaching an ELO rating of 1850 — the highest in our club history! Magnus has been on an incredible winning streak this season. Join us in celebrating his achievement at our next club night.',
        'days': -14,
    },
]

for data in announcements:
    Announcement.objects.get_or_create(
        title=data['title'],
        defaults={
            'body': data['body'],
            'published_at': now + timedelta(days=data['days']),
            'is_published': True,
            'author': admin_user,
        }
    )
print("  Created 3 announcements")

print("\nSample data created successfully!")
print("You can now run: python manage.py runserver")
print("Admin login: username=admin, password=admin123")
