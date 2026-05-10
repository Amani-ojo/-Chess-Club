from django.contrib.auth.models import User
from django.db import models
from django.utils.text import slugify


class Member(models.Model):
    user = models.OneToOneField(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='club_member',
    )
    display_name = models.CharField(max_length=150)
    lichess_username = models.CharField(max_length=100, blank=True)
    elo_rating = models.FloatField(
        default=1500.0,
        help_text='Over-the-board club Elo (updated when club matches are recorded).',
    )
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    draws = models.PositiveIntegerField(default=0)
    avatar = models.ImageField(upload_to='avatars/', blank=True)

    class Meta:
        ordering = ['display_name']

    def __str__(self):
        return self.display_name

    @property
    def games_played(self) -> int:
        return self.wins + self.losses + self.draws

    @property
    def win_percentage(self) -> float:
        if self.games_played == 0:
            return 0.0
        return round(100.0 * self.wins / self.games_played, 2)


class Match(models.Model):
    STATUS_SCHEDULED = 'scheduled'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, 'Scheduled'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    RESULT_WHITE = '1-0'
    RESULT_BLACK = '0-1'
    RESULT_DRAW = '1/2-1/2'
    RESULT_CHOICES = [
        ('', 'Pending'),
        (RESULT_WHITE, 'White wins'),
        (RESULT_BLACK, 'Black wins'),
        (RESULT_DRAW, 'Draw'),
    ]

    white_player = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name='matches_as_white',
    )
    black_player = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name='matches_as_black',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED)
    result = models.CharField(max_length=10, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    scheduled_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    elo_processed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-scheduled_at']
        verbose_name_plural = 'Matches'

    def __str__(self):
        return f'{self.white_player} vs {self.black_player} ({self.get_status_display()})'

    def save(self, *args, **kwargs):
        from django.db import transaction
        from django.utils import timezone

        with transaction.atomic():
            if self.status == self.STATUS_COMPLETED and self.result and not self.completed_at:
                self.completed_at = timezone.now()
            super().save(*args, **kwargs)
            if self.status == self.STATUS_COMPLETED and self.result:
                from club.services.match_elo import process_match_completion

                process_match_completion(self.__class__.objects.get(pk=self.pk))


class EloHistory(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='elo_history')
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='elo_entries')
    rating_before = models.FloatField()
    rating_after = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Elo histories'

    def __str__(self):
        return f'{self.member}: {self.rating_before:.1f} → {self.rating_after:.1f}'


class Announcement(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    published_at = models.DateTimeField()
    author = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title


class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.created_at:%Y-%m-%d})'


class Team(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:150] or 'team'
            slug = base
            n = 2
            while True:
                qs = Team.objects.filter(slug=slug)
                if self.pk:
                    qs = qs.exclude(pk=self.pk)
                if not qs.exists():
                    break
                suffix = f'-{n}'
                slug = f'{base[: 160 - len(suffix)]}{suffix}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


class TeamMembership(models.Model):
    ROLE_MEMBER = 'member'
    ROLE_CAPTAIN = 'captain'
    ROLE_CHOICES = [
        (ROLE_MEMBER, 'Member'),
        (ROLE_CAPTAIN, 'Captain'),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('team', 'member')]


class UserProfile(models.Model):
    THEME_CHOICES = [
        ('classic', 'Classic Light'),
        ('midnight', 'Midnight Dark'),
        ('forest', 'Forest Green'),
        ('royal', 'Royal Blue'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    lichess_username = models.CharField(max_length=100, blank=True)
    lichess_api_key = models.CharField(max_length=255, blank=True)
    theme_preference = models.CharField(max_length=20, choices=THEME_CHOICES, default='classic')
    last_lichess_sync_requested_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__username']

    def __str__(self):
        return f'Profile<{self.user.username}>'
