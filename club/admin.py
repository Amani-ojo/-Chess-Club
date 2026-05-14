from django.contrib import admin
feature/stockfish-analysis-improvements
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django_otp.admin import OTPAdminAuthenticationForm

from .models import (
    Announcement,
    ContactMessage,
    EloHistory,
    Match,
    Member,
    SwissPairing,
    SwissParticipant,
    SwissRound,
    SwissTournament,
    Team,
    TeamMembership,
    UserProfile,
)
from .services.match_elo import recalculate_all_club_elo
from .services.swiss_pairing import generate_next_swiss_round

admin.site.site_header = 'Eschen Chess Club Control Center'
admin.site.site_title = 'Eschen Chess Club Admin'
admin.site.index_title = 'Operations Dashboard'
admin.site.login_form = OTPAdminAuthenticationForm


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 1
    autocomplete_fields = ['member']


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        'display_name',
        'user',
        'lichess_username',
        'elo_rating',
        'wins',
        'losses',
        'draws',
        'games_played',
    )
    search_fields = ('display_name', 'lichess_username', 'user__username', 'user__email')
    autocomplete_fields = ['user']
    readonly_fields = ('wins', 'losses', 'draws')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'lichess_username', 'updated_at')
    search_fields = ('user__username', 'user__email', 'lichess_username')
    autocomplete_fields = ['user']


class SwissParticipantInline(admin.TabularInline):
    model = SwissParticipant
    extra = 1
    autocomplete_fields = ('member',)


class SwissPairingInline(admin.TabularInline):
    model = SwissPairing
    extra = 0
    autocomplete_fields = ('white', 'black')
    readonly_fields = ('club_match',)


@admin.register(SwissTournament)
class SwissTournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'rounds_played', 'rounds_target', 'counts_for_club_elo', 'created_at')
    list_filter = ('status', 'counts_for_club_elo')
    search_fields = ('name', 'slug', 'venue')
    readonly_fields = ('slug', 'rounds_played', 'created_at', 'updated_at')
    inlines = [SwissParticipantInline]
    actions = ('generate_next_round', 'mark_finished')

    @admin.action(description='Generate next Swiss round pairings')
    def generate_next_round(self, request, queryset):
        for t in queryset:
            rnd = generate_next_swiss_round(t)
            if rnd:
                self.message_user(request, f'Created round {rnd.number} for {t}.', messages.SUCCESS)
            else:
                self.message_user(request, f'Could not advance {t}: check players, limits, duplicates.', messages.WARNING)

    @admin.action(description='Mark tournament as finished')
    def mark_finished(self, request, queryset):
        n = queryset.update(status=SwissTournament.STATUS_DONE)
        self.message_user(request, f'Marked {n} tournament(s) finished.', messages.SUCCESS)


@admin.register(SwissRound)
class SwissRoundAdmin(admin.ModelAdmin):
    list_display = ('tournament', 'number', 'created_at')
    list_filter = ('tournament',)
    ordering = ('-tournament_id', '-number')
    inlines = [SwissPairingInline]
    autocomplete_fields = ('tournament',)
=======
from django.db import transaction

from .elo import calculate_elo
from .models import Announcement, EloHistory, Match, Member


def _apply_elo(match: Match) -> None:
    """Update both players' ratings and create EloHistory records for a completed match."""
    white = match.player_white
    black = match.player_black

    result = calculate_elo(
        white_elo=white.elo_rating,
        black_elo=black.elo_rating,
        white_games=white.total_games(),
        black_games=black.total_games(),
        result=match.result,
    )

    # Record history before mutating ratings
    EloHistory.objects.create(
        member=white,
        match=match,
        rating_before=white.elo_rating,
        rating_after=result.white_new,
    )
    EloHistory.objects.create(
        member=black,
        match=match,
        rating_before=black.elo_rating,
        rating_after=result.black_new,
    )

    # Update win/loss/draw counters
    if match.result == "white_wins":
        white.wins += 1
        black.losses += 1
    elif match.result == "black_wins":
        black.wins += 1
        white.losses += 1
    else:  # draw
        white.draws += 1
        black.draws += 1

    # Apply new ratings
    white.elo_rating = result.white_new
    black.elo_rating = result.black_new

    white.save()
    black.save()


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ["display_name", "elo_rating", "wins", "losses", "draws", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["display_name", "user__username"]
 develop


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
 feature/stockfish-analysis-improvements
    list_display = (
        'white_player',
        'black_player',
        'status',
        'result',
        'scheduled_at',
        'completed_at',
        'elo_processed',
    )
    list_filter = ('status', 'result')
    search_fields = (
        'white_player__display_name',
        'black_player__display_name',
        'venue',
    )
    autocomplete_fields = ['white_player', 'black_player']
    readonly_fields = ('elo_processed', 'swiss_pairing_display')
    actions = ['action_recalculate_club_elo']

    @admin.display(description='Swiss pairing')
    def swiss_pairing_display(self, obj):
        if not obj.pk:
            return ''
        try:
            return str(obj.swiss_pairing.round)
        except ObjectDoesNotExist:
            return ''

    @admin.action(description='Recalculate club ELO from all completed matches')
    def action_recalculate_club_elo(self, request, queryset):
        n = recalculate_all_club_elo()
        self.message_user(request, f'Recalculated ratings from {n} completed matches.', messages.SUCCESS)
=======
    list_display = ["player_white", "player_black", "scheduled_at", "venue", "status", "result"]
    list_filter = ["status", "result"]
    search_fields = ["player_white__display_name", "player_black__display_name", "venue"]
    actions = ["recalculate_all_elo"]

    def save_model(self, request, obj, form, change):
        """Auto-update ELO ratings when a match is marked completed with a result."""
        super().save_model(request, obj, form, change)

        is_newly_completed = (
            obj.status == "completed"
            and obj.result
            and not EloHistory.objects.filter(match=obj).exists()
        )

        if is_newly_completed:
            _apply_elo(obj)

    @admin.action(description="Recalculate all ELO ratings from match history")
    def recalculate_all_elo(self, request, queryset):
        """Reset every member to 1200 and replay all completed matches chronologically."""
        with transaction.atomic():
            # Reset all members
            Member.objects.update(elo_rating=1200, wins=0, losses=0, draws=0)

            # Clear existing history
            EloHistory.objects.all().delete()

            # Replay every completed match in chronological order
            completed = Match.objects.filter(
                status="completed",
                result__isnull=False,
            ).exclude(result="").order_by("scheduled_at")

            replayed = 0
            for match in completed:
                # Refresh from DB so each step sees the latest ratings
                match.player_white.refresh_from_db()
                match.player_black.refresh_from_db()
                _apply_elo(match)
                replayed += 1

        self.message_user(request, f"Recalculated ELO for {replayed} match(es).")
develop


@admin.register(EloHistory)
class EloHistoryAdmin(admin.ModelAdmin):
 feature/stockfish-analysis-improvements
    list_display = ('member', 'match', 'rating_before', 'rating_after', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('member__display_name',)
=======
    list_display = ["member", "rating_before", "rating_after", "recorded_at"]
    list_filter = ["member"]
 develop


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
 feature/stockfish-analysis-improvements
    list_display = ('title', 'published_at', 'author')
    list_filter = ('published_at',)
    search_fields = ('title', 'body')
    autocomplete_fields = ['author']


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at')
    search_fields = ('name', 'email', 'body')
    readonly_fields = ('name', 'email', 'body', 'created_at')


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')
    readonly_fields = ('slug',)
    inlines = [TeamMembershipInline]
=======
    list_display = ["title", "author", "published_at", "is_published"]
    list_filter = ["is_published"]
    search_fields = ["title", "body"]
 develop
