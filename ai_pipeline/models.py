from django.db import models

from club.models import Member


class Game(models.Model):
    lichess_game_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    player_white = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='lichess_games_as_white')
    player_black = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='lichess_games_as_black')
    pgn = models.TextField(help_text='Portable Game Notation of the full game')
    time_control = models.CharField(max_length=50, blank=True)
    result = models.CharField(max_length=10, help_text='e.g. 1-0, 0-1, 1/2-1/2')
    played_at = models.DateTimeField()
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-played_at']

    def __str__(self):
        return f'{self.player_white} vs {self.player_black} ({self.result})'


class GameAnalysis(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    game = models.OneToOneField(Game, on_delete=models.CASCADE, related_name='analysis')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    depth = models.IntegerField(default=20, help_text='Stockfish search depth used')
    white_avg_centipawn_loss = models.FloatField(null=True, blank=True)
    black_avg_centipawn_loss = models.FloatField(null=True, blank=True)
    white_blunders = models.IntegerField(default=0)
    black_blunders = models.IntegerField(default=0)
    white_mistakes = models.IntegerField(default=0)
    black_mistakes = models.IntegerField(default=0)
    white_inaccuracies = models.IntegerField(default=0)
    black_inaccuracies = models.IntegerField(default=0)
    analysed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Game Analyses'

    def __str__(self):
        return f'Analysis of {self.game} - {self.get_status_display()}'


class MoveEvaluation(models.Model):
    CLASSIFICATION_CHOICES = [
        ('best', 'Best'),
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('inaccuracy', 'Inaccuracy'),
        ('mistake', 'Mistake'),
        ('blunder', 'Blunder'),
    ]

    analysis = models.ForeignKey(GameAnalysis, on_delete=models.CASCADE, related_name='move_evaluations')
    move_number = models.IntegerField()
    is_white = models.BooleanField(help_text='True if this is a white move')
    move_san = models.CharField(max_length=10, help_text='Standard Algebraic Notation, e.g. Nf3')
    best_move_san = models.CharField(max_length=10, blank=True)
    eval_before = models.FloatField(help_text='Centipawn evaluation before the move')
    eval_after = models.FloatField(help_text='Centipawn evaluation after the move')
    centipawn_loss = models.FloatField(default=0)
    classification = models.CharField(max_length=20, choices=CLASSIFICATION_CHOICES, default='good')

    class Meta:
        ordering = ['analysis', 'move_number', '-is_white']

    def __str__(self):
        side = 'W' if self.is_white else 'B'
        return f'Move {self.move_number}{side}: {self.move_san} ({self.classification})'

    @staticmethod
    def format_eval_cp(cp):
        """Human-readable score from stored centipawns (±999 used as mate sentinel in analysis)."""
        if cp is None:
            return '—'
        try:
            v = float(cp)
        except (TypeError, ValueError):
            return '—'
        if v >= 998:
            return 'Mate (+)'
        if v <= -998:
            return 'Mate (−)'
        pawns = v / 100.0
        return f'{pawns:+.2f}'

    @property
    def eval_before_display(self):
        return self.format_eval_cp(self.eval_before)

    @property
    def eval_after_display(self):
        return self.format_eval_cp(self.eval_after)

    @property
    def eval_delta_for_mover_display(self):
        """Signed change from the moving side’s perspective (positive = improved for you)."""
        if self.eval_before is None or self.eval_after is None:
            return '—'
        try:
            before, after = float(self.eval_before), float(self.eval_after)
        except (TypeError, ValueError):
            return '—'
        if self.is_white:
            delta = after - before
        else:
            delta = before - after
        return f'{delta / 100.0:+.2f}'

    @property
    def ply_label(self) -> str:
        return f'{self.move_number}.' if self.is_white else f'{self.move_number}...'

    def study_headline(self) -> str:
        side = 'White' if self.is_white else 'Black'
        cls = self.classification or 'good'
        labels = {
            'best': f'{side} played the engine’s top choice.',
            'excellent': f'{side} played a move that is very close to best.',
            'good': f'{side} played a solid move with a small eval concession.',
            'inaccuracy': f'{side} played an imprecise move; accuracy slipped slightly.',
            'mistake': f'{side} made a mistake that clearly worsened the position.',
            'blunder': f'{side} blundered — a large swing in evaluation.',
        }
        return labels.get(cls, f'{side} played this move.')

    def study_paragraphs(self) -> list[str]:
        """Plain-text paragraphs for the interactive study view (left column)."""
        side = 'White' if self.is_white else 'Black'
        cpl = float(self.centipawn_loss or 0)
        cpl_i = int(round(cpl))
        best = (self.best_move_san or '').strip()
        eb = self.eval_before_display
        ea = self.eval_after_display
        delta = self.eval_delta_for_mover_display
        paras: list[str] = []

        paras.append(
            f'Before this half-move the engine scored the position as {eb} from White’s perspective '
            f'(positive favors White). After {self.move_san}, the score is {ea}. '
            f'For the side that moved, the swing in “their” favor is Δ = {delta} pawns.'
        )

        cls = self.classification or 'good'
        if cls == 'best':
            paras.append(
                f'{side} matched Stockfish’s first line. There is nothing stronger to find at this depth — '
                'the main learning point is to recognize why this move works tactically and positionally.'
            )
        elif cls in ('excellent', 'good'):
            if best and best != self.move_san:
                paras.append(
                    f'The engine’s principal alternative was {best}. Your move was still within a healthy margin; '
                    f'study {best} briefly to see if it improves piece activity, king safety, or structure in ways you want to internalize.'
                )
            else:
                paras.append(
                    'There was no meaningful gap to the top engine reply. Reinforce the plan behind this move '
                    'so you can reproduce similar decisions in analogous positions.'
                )
        elif cls == 'inaccuracy':
            if best:
                paras.append(
                    f'{best} keeps coordination tighter. The centipawn loss is about {cpl_i} cp — small in isolation but '
                    'these margins add up; compare king safety, piece placement, and pawn tension after both moves.'
                )
            else:
                paras.append(
                    f'About {cpl_i} cp drifted away. Re-run candidate moves: one extra pass for hanging pieces and checks '
                    'often catches the improvement the engine prefers.'
                )
        elif cls == 'mistake':
            if best:
                paras.append(
                    f'Prefer {best} here: it addresses the tactical or structural issue more directly. '
                    f'Roughly {cpl_i} cp separates your choice from the engine line — worth a slow replay on the board.'
                )
            else:
                paras.append(
                    'The evaluation drops meaningfully. Look for undefended pieces, loose king cover, or a change in the pawn structure '
                    'that your move failed to respect.'
                )
        else:  # blunder
            if best:
                paras.append(
                    f'{best} was dramatically stronger. A loss of about {cpl_i} cp usually means a tactical oversight or a strategic '
                    'misjudgment; step through forcing lines (checks, captures, threats) before replaying your move.'
                )
            else:
                paras.append(
                    'The position collapses after this choice. Treat it as a pattern to memorize: what signal did you miss on the previous move?'
                )

        paras.append(
            'Use the board on the right: compare your move with the engine suggestion from the same position, then step forward when you are ready.'
        )
        return paras


class PlayerInsight(models.Model):
    CATEGORY_CHOICES = [
        ('opening', 'Opening'),
        ('middlegame', 'Middlegame'),
        ('endgame', 'Endgame'),
        ('tactics', 'Tactics'),
        ('time_management', 'Time Management'),
        ('positional', 'Positional Play'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='insights')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField(help_text='Detailed insight with examples')
    recommendation = models.TextField(help_text='Suggested improvement actions')
    games_analysed = models.IntegerField(default=0)
    avg_centipawn_loss = models.FloatField(null=True, blank=True)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f'{self.member} - {self.title}'
