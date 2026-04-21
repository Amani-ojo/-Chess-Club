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

    def __str__(self):
        return self.display_name

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

    class Meta:
        ordering = ['-scheduled_at']
        verbose_name_plural = 'Matches'

    def __str__(self):
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

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title
