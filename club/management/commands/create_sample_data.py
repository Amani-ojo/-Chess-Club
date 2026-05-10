"""Seed deterministic demo OTB matches, announcements, and members for staging / Codespaces."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from club.models import Announcement, Match, Member, Team, TeamMembership

User = get_user_model()

# Tagged data can be wiped with --purge-demo (lichess_username suffix + venue substring).
MEMBER_SPECS = [
    ('Marie Weber', 'marie_eschen_demo'),
    ('Luca Büchel', 'luca_eschen_demo'),
    ('Nina Klaus', 'nina_eschen_demo'),
    ('Jonas Quaderer', 'jonas_eschen_demo'),
    ('Sophie Meier', 'sophie_eschen_demo'),
    ('Markus Schädler', 'markus_eschen_demo'),
    ('Elena Beck', 'elena_eschen_demo'),
    ('Bruno Marxer', 'bruno_eschen_demo'),
    ('Alice Club', 'alice_club_demo'),
    ('Bob Club', 'bob_club_demo'),
]

ANNOUNCEMENTS = [
    (
        '[Demo] Autumn rapid league begins 15 October',
        'Round-robin at the club hall starts next week; pairings publish after close of registrations. Volunteers for setup: reply on the bulletin board.',
    ),
    (
        '[Demo] New digital pairings kiosk',
        'The entrance tablet now mirrors today’s scheduled boards. Speak to Markus if pairing software shows stale data;',
    ),
    (
        '[Demo] Youth ladder — Sunday mornings',
        'Beginners welcome 09:45 at Schulhaus Eschen; coaches Nora and Luca rotate weekly.',
    ),
    (
        '[Demo] FIDE handbook update',
        'Tournament organisers: default time controls for club events now follow appendix guidelines published this month;',
    ),
    (
        '[Demo] Welcome to the Eschen public portal',
        'Announcements and OTB results stay on this site; members can optionally link personal Lichess accounts from the dashboard after login.',
    ),
]


class Command(BaseCommand):
    help = 'Seed Eschen-themed demo members, announcements, scheduled matches, and OTB history (optional --purge-demo).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-club-stats',
            action='store_true',
            help='Clear all OTB matches and ELO history, reset member club ratings.',
        )
        parser.add_argument(
            '--purge-demo',
            action='store_true',
            help='Remove previously seeded demo entities (members with *_eschen_demo / *_club_demo, venue containing [demo], titles starting [Demo]).',
        )

    def handle(self, *args, **options):
        from club.models import EloHistory
        from club.services.match_elo import recalculate_all_club_elo

        if options['purge_demo']:
            self._purge_demo()
        if options['reset_club_stats']:
            Match.objects.all().delete()
            EloHistory.objects.all().delete()
            Member.objects.all().update(elo_rating=1500.0, wins=0, losses=0, draws=0)
            self.stdout.write(self.style.WARNING('Cleared OTB matches, ELO history, and reset club ratings.'))

        with transaction.atomic():
            admin_user, created = User.objects.get_or_create(
                username='admin',
                defaults={'email': 'admin@example.com', 'is_staff': True, 'is_superuser': True},
            )
            if created:
                admin_user.set_password('admin')
                admin_user.save()

            members = []
            for display_name, lichess in MEMBER_SPECS:
                m, _ = Member.objects.get_or_create(
                    lichess_username=lichess,
                    defaults={'display_name': display_name},
                )
                if m.display_name != display_name:
                    m.display_name = display_name
                    m.save(update_fields=['display_name'])
                members.append(m)

            by_lichess = {m.lichess_username: m for m in members}
            now = timezone.now()
            venue_demo = 'Eschen club hall · [demo]'

            # Upcoming — stable offsets from "now"
            upcoming_specs = [
                (by_lichess['marie_eschen_demo'], by_lichess['luca_eschen_demo'], now + timedelta(days=2, hours=18)),
                (by_lichess['nina_eschen_demo'], by_lichess['jonas_eschen_demo'], now + timedelta(days=5, hours=17, minutes=30)),
                (by_lichess['sophie_eschen_demo'], by_lichess['markus_eschen_demo'], now + timedelta(days=9, hours=14)),
                (
                    by_lichess['elena_eschen_demo'],
                    by_lichess['bruno_eschen_demo'],
                    now + timedelta(days=12, hours=19),
                ),
                (
                    by_lichess['alice_club_demo'],
                    by_lichess['bob_club_demo'],
                    now + timedelta(days=14, hours=16),
                ),
            ]
            for white, black, start in upcoming_specs:
                if not Match.objects.filter(
                    white_player=white,
                    black_player=black,
                    scheduled_at=start,
                ).exists():
                    Match.objects.create(
                        white_player=white,
                        black_player=black,
                        status=Match.STATUS_SCHEDULED,
                        venue=venue_demo,
                        scheduled_at=start,
                    )

            # Historical completed — deterministic spread of results (applied in order below)
            base = now - timedelta(days=120)
            completed_rows = [
                (by_lichess['marie_eschen_demo'], by_lichess['luca_eschen_demo'], Match.RESULT_WHITE, base),
                (by_lichess['nina_eschen_demo'], by_lichess['sophie_eschen_demo'], Match.RESULT_BLACK, base + timedelta(days=7)),
                (by_lichess['markus_eschen_demo'], by_lichess['marie_eschen_demo'], Match.RESULT_DRAW, base + timedelta(days=14)),
                (by_lichess['luca_eschen_demo'], by_lichess['jonas_eschen_demo'], Match.RESULT_WHITE, base + timedelta(days=21)),
                (by_lichess['bruno_eschen_demo'], by_lichess['elena_eschen_demo'], Match.RESULT_WHITE, base + timedelta(days=28)),
                (by_lichess['alice_club_demo'], by_lichess['bob_club_demo'], Match.RESULT_WHITE, base + timedelta(days=35)),
                (by_lichess['bob_club_demo'], by_lichess['alice_club_demo'], Match.RESULT_DRAW, base + timedelta(days=42)),
                (by_lichess['sophie_eschen_demo'], by_lichess['nina_eschen_demo'], Match.RESULT_WHITE, base + timedelta(days=49)),
                (by_lichess['jonas_eschen_demo'], by_lichess['markus_eschen_demo'], Match.RESULT_BLACK, base + timedelta(days=56)),
                (by_lichess['elena_eschen_demo'], by_lichess['marie_eschen_demo'], Match.RESULT_BLACK, base + timedelta(days=63)),
                (by_lichess['marie_eschen_demo'], by_lichess['bruno_eschen_demo'], Match.RESULT_WHITE, base + timedelta(days=70)),
                (by_lichess['markus_eschen_demo'], by_lichess['luca_eschen_demo'], Match.RESULT_DRAW, base + timedelta(days=77)),
            ]
            for white, black, result, scheduled in completed_rows:
                completed_at = scheduled + timedelta(hours=3)
                if Match.objects.filter(white_player=white, black_player=black, scheduled_at=scheduled).exists():
                    continue
                Match.objects.create(
                    white_player=white,
                    black_player=black,
                    status=Match.STATUS_COMPLETED,
                    result=result,
                    venue=venue_demo,
                    scheduled_at=scheduled,
                    completed_at=completed_at,
                )

            for idx, (title, body) in enumerate(ANNOUNCEMENTS):
                published = now - timedelta(days=idx * 4 + 1)
                ann, created = Announcement.objects.get_or_create(
                    title=title,
                    defaults={'body': body, 'published_at': published, 'author': admin_user},
                )
                if not created:
                    ann.body = body
                    ann.published_at = published
                    ann.author = admin_user
                    ann.save()

            team, _ = Team.objects.get_or_create(
                name='Eschen Rapid Squad',
                defaults={'description': 'Weekly OTB rapid practice squad (demo team).'},
            )
            for m in members[:8]:
                TeamMembership.objects.get_or_create(team=team, member=m, defaults={'role': TeamMembership.ROLE_MEMBER})

        # Single rebuild guarantees W/L/ELO coherence if any rows were skipped mid-flight
        n = recalculate_all_club_elo()
        self.stdout.write(self.style.SUCCESS(f'Demo seeded; replayed {n} completed matches for OTB ratings.'))

    def _purge_demo(self):
        """Remove identifiable demo residue so re-seeding stays clean."""
        demo_usernames_suffixes = ('_eschen_demo', '_club_demo')
        qs_members = Member.objects.filter(
            lichess_username__in=[spec[1] for spec in MEMBER_SPECS],
        )
        total_deleted, _by_model = qs_members.delete()
        self.stdout.write(
            self.style.WARNING(f'Removed demo graph ({total_deleted} database rows including dependent matches/history).')
        )

        Announcement.objects.filter(title__startswith='[Demo]').delete()
