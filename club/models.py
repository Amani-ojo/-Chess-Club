feature/stockfish-analysis-improvements
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
=======
from django.db import models
from django.contrib.auth.models import User


class Member(models.Model):
    """
    Represents a chess club member.
    Each member is linked to a Django User account for login.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=100)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    elo_rating = models.IntegerField(default=1200)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    joined_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-elo_rating']
 develop

    def __str__(self):
        return self.display_name

 feature/stockfish-analysis-improvements
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

    def total_games(self):
        return self.wins + self.losses + self.draws

    def win_percentage(self):
        total = self.total_games()
        if total == 0:
            return 0
        return round((self.wins / total) * 100, 1)


class Match(models.Model):
    """
    Represents a chess match between two members.
    """
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    RESULT_CHOICES = [
        ('white_wins', 'White Wins'),
        ('black_wins', 'Black Wins'),
        ('draw', 'Draw'),
    ]

    player_white = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name='matches_as_white'
    )
    player_black = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name='matches_as_black'
    )
    scheduled_at = models.DateTimeField()
    venue = models.CharField(max_length=200)
    round_number = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, blank=True, null=True)
    notes = models.TextField(blank=True)
 develop

    class Meta:
        ordering = ['-scheduled_at']
        verbose_name_plural = 'Matches'

    def __str__(self):
 feature/stockfish-analysis-improvements
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
=======
        return f"{self.player_white} vs {self.player_black} — {self.get_status_display()}"


class EloHistory(models.Model):
    """
    Tracks ELO rating changes over time for each member.
    A new record is created every time a match result is recorded.
    """
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='elo_history')
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='elo_changes')
    rating_before = models.IntegerField()
    rating_after = models.IntegerField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        verbose_name_plural = 'ELO Histories'

    def __str__(self):
        return f"{self.member} : {self.rating_before} → {self.rating_after}"


class Announcement(models.Model):
    """
    News items displayed on the home page.
    Managed by administrators via the Django Admin panel.
    """
    title = models.CharField(max_length=200)
    body = models.TextField()
    published_at = models.DateTimeField()
    is_published = models.BooleanField(default=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
 develop

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title
 feature/stockfish-analysis-improvements


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


class SwissTournament(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_DONE = 'done'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_DONE, 'Finished'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    rounds_played = models.PositiveSmallIntegerField(default=0)
    rounds_target = models.PositiveSmallIntegerField(
        default=5,
        help_text='Maximum Swiss rounds (organisers usually set near ceil(log2(n))).',
    )
    venue = models.CharField(max_length=200, blank=True)
    counts_for_club_elo = models.BooleanField(
        default=True,
        help_text='When results are recorded, create/update OTB Match rows so club ELO updates.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:200] or 'tournament'
            slug = base
            n = 2
            while True:
                qs = SwissTournament.objects.filter(slug=slug)
                if self.pk:
                    qs = qs.exclude(pk=self.pk)
                if not qs.exists():
                    break
                suffix = f'-{n}'
                slug = f'{base[: 220 - len(suffix)]}{suffix}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


class SwissParticipant(models.Model):
    tournament = models.ForeignKey(SwissTournament, on_delete=models.CASCADE, related_name='participants')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='swiss_entries')

    class Meta:
        unique_together = [('tournament', 'member')]

    def __str__(self):
        return f'{self.member} → {self.tournament.name}'


class SwissRound(models.Model):
    tournament = models.ForeignKey(SwissTournament, on_delete=models.CASCADE, related_name='rounds')
    number = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['number']
        unique_together = [('tournament', 'number')]

    def __str__(self):
        return f'{self.tournament.name} · Round {self.number}'


class SwissPairing(models.Model):
    RESULT_CHOICES = Match.RESULT_CHOICES

    round = models.ForeignKey(SwissRound, on_delete=models.CASCADE, related_name='pairings')
    board = models.PositiveSmallIntegerField(default=1)
    white = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='swiss_pairings_white')
    black = models.ForeignKey(Member, null=True, blank=True, on_delete=models.CASCADE, related_name='swiss_pairings_black')
    result = models.CharField(max_length=10, blank=True, choices=RESULT_CHOICES)
    club_match = models.OneToOneField(
        'Match',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='swiss_pairing',
        help_text='Linked OTB club match when this pairing counts for official ELO.',
    )

    class Meta:
        ordering = ['board']
        unique_together = [('round', 'board')]

    def __str__(self):
        if self.black_id:
            return f'Bd{self.board}: {self.white} vs {self.black}'
        return f'Bd{self.board}: {self.white} (bye)'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from club.services.swiss_otb_bridge import upsert_match_for_pairing

        upsert_match_for_pairing(self)


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
=======
 develop
