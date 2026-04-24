from django.contrib import admin

from .models import Member, UserProfile

admin.site.site_header = 'Eschen Chess Club Control Center'
admin.site.site_title = 'Eschen Chess Club Admin'
admin.site.index_title = 'Operations Dashboard'


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'lichess_username')
    search_fields = ('display_name', 'lichess_username')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'lichess_username', 'updated_at')
    search_fields = ('user__username', 'user__email', 'lichess_username')
