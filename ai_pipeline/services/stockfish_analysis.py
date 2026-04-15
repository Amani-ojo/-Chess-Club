"""
Stockfish analysis service — evaluates positions and classifies moves.

Uses the `stockfish` Python package (pip install stockfish) and
`python-chess` for PGN parsing.
"""

import io
import logging

import chess
import chess.pgn
from django.conf import settings
from stockfish import Stockfish

logger = logging.getLogger(__name__)

# Centipawn loss thresholds for move classification
THRESHOLDS = {
    'best':       0,
    'excellent':  10,
    'good':       25,
    'inaccuracy': 50,
    'mistake':    100,
    'blunder':    200,
}

# Cap raw centipawn evaluations to avoid distortion from forced-mate scores
EVAL_CAP = 1000


def classify_move(centipawn_loss):
    """Return a classification label based on centipawn loss for one move."""
    if centipawn_loss <= THRESHOLDS['best']:
        return 'best'
    elif centipawn_loss <= THRESHOLDS['excellent']:
        return 'excellent'
    elif centipawn_loss <= THRESHOLDS['good']:
        return 'good'
    elif centipawn_loss <= THRESHOLDS['inaccuracy']:
        return 'inaccuracy'
    elif centipawn_loss <= THRESHOLDS['mistake']:
        return 'mistake'
    else:
        return 'blunder'


def get_stockfish_engine():
    """Create and return a configured Stockfish instance."""
    engine = Stockfish(
        path=settings.STOCKFISH_PATH,
        depth=settings.STOCKFISH_DEPTH,
        parameters={
            'Threads': settings.STOCKFISH_THREADS,
            'Hash': settings.STOCKFISH_HASH_MB,
        },
    )
    return engine


def _get_eval(engine, board):
    """
    Return the centipawn evaluation from White's perspective for the
    current board position. Mate scores are capped at ±EVAL_CAP.
    """
    engine.set_fen_position(board.fen())
    evaluation = engine.get_evaluation()

    if evaluation['type'] == 'mate':
        return EVAL_CAP if evaluation['value'] > 0 else -EVAL_CAP

    raw = evaluation['value']
    return max(-EVAL_CAP, min(EVAL_CAP, raw))


def analyse_game(pgn_string):
    """
    Walk through every move in a game and evaluate it with Stockfish.

    Returns a dict:
    {
        'moves': [
            {
                'move_number':    int,
                'is_white':       bool,
                'move_san':       str,
                'best_move_san':  str,
                'eval_before':    float,   # centipawns, White's POV
                'eval_after':     float,
                'centipawn_loss': float,   # always >= 0
                'classification': str,
            },
            ...
        ],
        'white_avg_cpl':    float,
        'black_avg_cpl':    float,
        'white_blunders':   int,
        'black_blunders':   int,
        'white_mistakes':   int,
        'black_mistakes':   int,
        'white_inaccuracies': int,
        'black_inaccuracies': int,
    }
    """
    game = chess.pgn.read_game(io.StringIO(pgn_string))
    if game is None:
        raise ValueError('Could not parse PGN string — no game found.')

    engine = get_stockfish_engine()
    board = game.board()

    move_results = []
    white_cpls = []
    black_cpls = []

    counters = {
        'white_blunders': 0, 'black_blunders': 0,
        'white_mistakes': 0, 'black_mistakes': 0,
        'white_inaccuracies': 0, 'black_inaccuracies': 0,
    }

    for move_number, node in enumerate(game.mainline(), start=1):
        move = node.move
        is_white = board.turn == chess.WHITE

        eval_before = _get_eval(engine, board)

        engine.set_fen_position(board.fen())
        best_move_uci = engine.get_best_move()
        best_move_san = ''
        if best_move_uci:
            try:
                best_move_san = board.san(chess.Move.from_uci(best_move_uci))
            except Exception:
                best_move_san = best_move_uci

        move_san = board.san(move)
        board.push(move)

        eval_after = _get_eval(engine, board)

        # Centipawn loss: from the perspective of the side that just moved.
        # A drop in White's score is White's loss; a rise is Black's loss.
        if is_white:
            cpl = max(0.0, eval_before - eval_after)
        else:
            cpl = max(0.0, eval_after - eval_before)

        classification = classify_move(cpl)
        side = 'white' if is_white else 'black'

        if classification == 'blunder':
            counters[f'{side}_blunders'] += 1
        elif classification == 'mistake':
            counters[f'{side}_mistakes'] += 1
        elif classification == 'inaccuracy':
            counters[f'{side}_inaccuracies'] += 1

        if is_white:
            white_cpls.append(cpl)
        else:
            black_cpls.append(cpl)

        move_results.append({
            'move_number':    (move_number + 1) // 2,
            'is_white':       is_white,
            'move_san':       move_san,
            'best_move_san':  best_move_san,
            'eval_before':    eval_before,
            'eval_after':     eval_after,
            'centipawn_loss': round(cpl, 2),
            'classification': classification,
        })

    white_avg_cpl = round(sum(white_cpls) / len(white_cpls), 2) if white_cpls else 0.0
    black_avg_cpl = round(sum(black_cpls) / len(black_cpls), 2) if black_cpls else 0.0

    logger.info(
        'Analysis complete — %d moves | White avg CPL: %.1f | Black avg CPL: %.1f',
        len(move_results), white_avg_cpl, black_avg_cpl,
    )

    return {
        'moves':               move_results,
        'white_avg_cpl':       white_avg_cpl,
        'black_avg_cpl':       black_avg_cpl,
        **counters,
    }
