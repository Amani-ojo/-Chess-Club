from django.contrib import admin
from .models import Member, Match, EloHistory, Announcement
from .utils import calculate_elo, get_k_factor


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    """Admin configuration for the Member model."""
    list_display = ['display_name', 'elo_rating', 'wins', 'losses', 'draws', 'is_active']
    list_filter = ['is_active']
    search_fields = ['display_name', 'user__username']
    actions = ['recalculate_elo']

    def recalculate_elo(self, request, queryset):
        """Admin action to recalculate all ELO ratings from match history."""
        # Reset all members to starting ELO
        Member.objects.all().update(elo_rating=1200, wins=0, losses=0, draws=0)

        # Replay all completed matches in chronological order
        all_matches = Match.objects.filter(status='completed').order_by('scheduled_at')
        for match in all_matches:
            if match.result:
                white = match.player_white
                black = match.player_black
                white.refresh_from_db()
                black.refresh_from_db()

                k_white = get_k_factor(white)
                k_black = get_k_factor(black)

                if match.result == 'white_wins':
                    new_white = calculate_elo(white.elo_rating, black.elo_rating, 1, k_white)
                    new_black = calculate_elo(black.elo_rating, white.elo_rating, 0, k_black)
                    white.wins += 1
                    black.losses += 1
                elif match.result == 'black_wins':
                    new_white = calculate_elo(white.elo_rating, black.elo_rating, 0, k_white)
                    new_black = calculate_elo(black.elo_rating, white.elo_rating, 1, k_black)
                    white.losses += 1
                    black.wins += 1
                else:  # draw
                    new_white = calculate_elo(white.elo_rating, black.elo_rating, 0.5, k_white)
                    new_black = calculate_elo(black.elo_rating, white.elo_rating, 0.5, k_black)
                    white.draws += 1
                    black.draws += 1

                white.elo_rating = new_white
                black.elo_rating = new_black
                white.save()
                black.save()

        self.message_user(request, 'ELO ratings recalculated successfully.')

    recalculate_elo.short_description = 'Recalculate ELO from history'


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    """Admin configuration for the Match model."""
    list_display = ['player_white', 'player_black', 'scheduled_at', 'venue', 'status', 'result']
    list_filter = ['status', 'result']
    search_fields = ['player_white__display_name', 'player_black__display_name', 'venue']

    def save_model(self, request, obj, form, change):
        """
        When a match result is saved, automatically update ELO ratings
        for both players and create EloHistory records.
        """
        super().save_model(request, obj, form, change)

        # Only update ELO when status is completed and result is set
        if obj.status == 'completed' and obj.result:
            white = obj.player_white
            black = obj.player_black

            k_white = get_k_factor(white)
            k_black = get_k_factor(black)

            old_white = white.elo_rating
            old_black = black.elo_rating

            if obj.result == 'white_wins':
                white.elo_rating = calculate_elo(old_white, old_black, 1, k_white)
                black.elo_rating = calculate_elo(old_black, old_white, 0, k_black)
                white.wins += 1
                black.losses += 1
            elif obj.result == 'black_wins':
                white.elo_rating = calculate_elo(old_white, old_black, 0, k_white)
                black.elo_rating = calculate_elo(old_black, old_white, 1, k_black)
                white.losses += 1
                black.wins += 1
            else:  # draw
                white.elo_rating = calculate_elo(old_white, old_black, 0.5, k_white)
                black.elo_rating = calculate_elo(old_black, old_white, 0.5, k_black)
                white.draws += 1
                black.draws += 1

            white.save()
            black.save()

            # Create ELO history records for both players
            EloHistory.objects.create(
                member=white, match=obj,
                rating_before=old_white, rating_after=white.elo_rating
            )
            EloHistory.objects.create(
                member=black, match=obj,
                rating_before=old_black, rating_after=black.elo_rating
            )


@admin.register(EloHistory)
class EloHistoryAdmin(admin.ModelAdmin):
    """Admin configuration for the EloHistory model."""
    list_display = ['member', 'rating_before', 'rating_after', 'recorded_at']
    list_filter = ['member']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    """Admin configuration for the Announcement model."""
    list_display = ['title', 'author', 'published_at', 'is_published']
    list_filter = ['is_published']
    search_fields = ['title', 'body']
