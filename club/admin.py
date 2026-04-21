from django.contrib import admin
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


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
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


@admin.register(EloHistory)
class EloHistoryAdmin(admin.ModelAdmin):
    list_display = ["member", "rating_before", "rating_after", "recorded_at"]
    list_filter = ["member"]


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "published_at", "is_published"]
    list_filter = ["is_published"]
    search_fields = ["title", "body"]
