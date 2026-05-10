from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from club.models import Announcement, Match, Member, Team, TeamMembership

User = get_user_model()


class Command(BaseCommand):
    help = 'Create demonstration club matches, announcements, and teams without touching imported Lichess games.'

    def add_arguments(self, parser):
        parser.add_argument('--reset-club-stats', action='store_true', help='Zero club W/L/D and ELO before seeding.')

    def handle(self, *args, **options):
        from club.models import EloHistory

        if options['reset_club_stats']:
            Match.objects.all().delete()
            EloHistory.objects.all().delete()
            Member.objects.all().update(elo_rating=1500.0, wins=0, losses=0, draws=0)
            self.stdout.write(self.style.WARNING('Cleared OTB matches, ELO history, and reset club ratings.'))

        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@example.com', 'is_staff': True, 'is_superuser': True},
        )
        if created:
            admin_user.set_password('admin')
            admin_user.save()

        alice, _ = Member.objects.get_or_create(
            display_name='Alice Club',
            defaults={'lichess_username': 'alice_club_demo', 'elo_rating': 1500.0},
        )
        bob, _ = Member.objects.get_or_create(
            display_name='Bob Club',
            defaults={'lichess_username': 'bob_club_demo', 'elo_rating': 1500.0},
        )

        now = timezone.now()
        Match.objects.get_or_create(
            white_player=alice,
            black_player=bob,
            scheduled_at=now + timedelta(days=3),
            defaults={'status': Match.STATUS_SCHEDULED, 'venue': 'Club hall'},
        )

        Match.objects.create(
            white_player=alice,
            black_player=bob,
            status=Match.STATUS_COMPLETED,
            result=Match.RESULT_WHITE,
            venue='Club hall',
            scheduled_at=now - timedelta(days=10),
            completed_at=now - timedelta(days=9),
        )

        Match.objects.create(
            white_player=bob,
            black_player=alice,
            status=Match.STATUS_COMPLETED,
            result=Match.RESULT_DRAW,
            venue='Club hall',
            scheduled_at=now - timedelta(days=5),
            completed_at=now - timedelta(days=4),
        )

        Announcement.objects.get_or_create(
            title='Welcome to the new Eschen dashboards',
            defaults={
                'body': 'Imported Lichess games and club matches now live alongside each other. Use the leaderboard and matches pages.',
                'published_at': now,
                'author': admin_user if admin_user.pk else None,
            },
        )

        team, _ = Team.objects.get_or_create(
            name='Eschen Rapid Squad',
            defaults={'description': 'Weekly rapid practice OTB squad.'},
        )
        TeamMembership.objects.get_or_create(team=team, member=alice, defaults={'role': TeamMembership.ROLE_MEMBER})
        TeamMembership.objects.get_or_create(team=team, member=bob, defaults={'role': TeamMembership.ROLE_MEMBER})

        self.stdout.write(self.style.SUCCESS('Sample OTB matches, announcements, and team seeded.'))
