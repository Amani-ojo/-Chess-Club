"""
Insight aggregation — analyses multiple games to find weakness patterns
and generate improvement recommendations for a player.
"""

import logging
from collections import defaultdict

from ai_pipeline.models import GameAnalysis, MoveEvaluation, PlayerInsight

logger = logging.getLogger(__name__)

# Game phase boundaries (by move number, per-side count)
OPENING_END    = 15
MIDDLEGAME_END = 35

# Minimum blunder/mistake rate (per game) to trigger a recommendation
BLUNDER_THRESHOLD  = 1.5
MISTAKE_THRESHOLD  = 2.0
CPL_HIGH_THRESHOLD = 60.0


def _phase(move_number):
    """Map a move number to a game phase label."""
    if move_number <= OPENING_END:
        return 'opening'
    elif move_number <= MIDDLEGAME_END:
        return 'middlegame'
    else:
        return 'endgame'


def _build_insight(member, category, title, description, recommendation,
                   games_analysed, avg_cpl):
    """Create or update a single PlayerInsight record."""
    PlayerInsight.objects.update_or_create(
        member=member,
        category=category,
        title=title,
        defaults={
            'description':     description,
            'recommendation':  recommendation,
            'games_analysed':  games_analysed,
            'avg_centipawn_loss': avg_cpl,
        },
    )


def aggregate_insights(member):
    """
    Process all completed game analyses for a member and generate
    PlayerInsight records covering opening, middlegame, endgame, and
    tactics weaknesses.
    """
    completed_analyses = GameAnalysis.objects.filter(
        status='completed',
    ).filter(
        game__player_white=member
    ) | GameAnalysis.objects.filter(
        status='completed',
    ).filter(
        game__player_black=member
    )

    completed_analyses = completed_analyses.distinct().select_related('game')

    if not completed_analyses.exists():
        logger.info('aggregate_insights: No completed analyses for member %s.', member)
        return

    game_count = completed_analyses.count()

    phase_cpls    = defaultdict(list)
    phase_blunders = defaultdict(int)
    phase_mistakes = defaultdict(int)

    for analysis in completed_analyses:
        is_white = analysis.game.player_white == member

        evals = MoveEvaluation.objects.filter(
            analysis=analysis,
            is_white=is_white,
        )

        for ev in evals:
            phase = _phase(ev.move_number)
            phase_cpls[phase].append(ev.centipawn_loss)
            if ev.classification == 'blunder':
                phase_blunders[phase] += 1
            elif ev.classification == 'mistake':
                phase_mistakes[phase] += 1

    phase_label_map = {
        'opening':    'Opening',
        'middlegame': 'Middlegame',
        'endgame':    'Endgame',
    }

    recommendations_map = {
        'opening': (
            'Review common opening principles: control the centre, '
            'develop knights before bishops, and castle early. '
            'Consider studying 2-3 solid openings thoroughly rather than many superficially.'
        ),
        'middlegame': (
            'Practice tactical puzzles daily (pins, forks, skewers, discovered attacks). '
            'Before each move, ask: "Is my opponent threatening anything? '
            'Can I create a threat of my own?"'
        ),
        'endgame': (
            'Study fundamental endgame techniques: king and pawn endings, '
            'rook endings, and opposition. Activate your king early in the endgame.'
        ),
    }

    for phase in ['opening', 'middlegame', 'endgame']:
        cpls = phase_cpls[phase]
        if not cpls:
            continue

        avg_cpl        = round(sum(cpls) / len(cpls), 2)
        blunders_rate  = phase_blunders[phase] / game_count
        mistakes_rate  = phase_mistakes[phase] / game_count

        if avg_cpl < CPL_HIGH_THRESHOLD and blunders_rate < BLUNDER_THRESHOLD:
            continue

        label = phase_label_map[phase]
        description = (
            f'Across {game_count} analysed game(s), your average centipawn loss '
            f'in the {label.lower()} was {avg_cpl:.1f}. '
            f'You averaged {blunders_rate:.1f} blunder(s) and '
            f'{mistakes_rate:.1f} mistake(s) per game in this phase.'
        )

        _build_insight(
            member=member,
            category=phase,
            title=f'{label} Accuracy — Needs Improvement',
            description=description,
            recommendation=recommendations_map[phase],
            games_analysed=game_count,
            avg_cpl=avg_cpl,
        )

    total_blunders = sum(phase_blunders.values())
    if total_blunders / game_count >= BLUNDER_THRESHOLD:
        _build_insight(
            member=member,
            category='tactics',
            title='Tactical Awareness — Recurring Blunders Detected',
            description=(
                f'You averaged {total_blunders / game_count:.1f} blunder(s) per game '
                f'across {game_count} game(s). Blunders often result from missing '
                f'opponent threats or one-move tactical patterns.'
            ),
            recommendation=(
                'Spend 10-15 minutes daily on tactics puzzles (Chess.com Puzzles or '
                'Lichess Puzzles). Focus on recognising threats before making your move.'
            ),
            games_analysed=game_count,
            avg_cpl=None,
        )

    logger.info(
        'aggregate_insights: Insights generated for member %s across %d game(s).',
        member, game_count,
    )
