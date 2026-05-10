from django.contrib import admin
from django.contrib import messages
from django_otp.admin import OTPAdminAuthenticationForm

from .models import (
    Announcement,
    ContactMessage,
    EloHistory,
    Match,
    Member,
    Team,
    TeamMembership,
    UserProfile,
)
from .services.match_elo import recalculate_all_club_elo

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


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
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
    readonly_fields = ('elo_processed',)
    actions = ['action_recalculate_club_elo']

    @admin.action(description='Recalculate club ELO from all completed matches')
    def action_recalculate_club_elo(self, request, queryset):
        n = recalculate_all_club_elo()
        self.message_user(request, f'Recalculated ratings from {n} completed matches.', messages.SUCCESS)


@admin.register(EloHistory)
class EloHistoryAdmin(admin.ModelAdmin):
    list_display = ('member', 'match', 'rating_before', 'rating_after', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('member__display_name',)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
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
