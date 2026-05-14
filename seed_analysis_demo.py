"""Seed a single analyzed game so the new analysis UI sections can be exercised locally.

Run with:  python manage.py shell < seed_analysis_demo.py
"""
from datetime import datetime, timezone
from django.contrib.auth import get_user_model

from club.models import Member
from ai_pipeline.models import Game, GameAnalysis, MoveEvaluation

User = get_user_model()

# --- Users + Members ----------------------------------------------------------
def ensure_member(username: str, display: str, lichess_username: str) -> Member:
    user, _ = User.objects.get_or_create(
        username=username,
        defaults={'email': f'{username}@example.com'},
    )
    member, _ = Member.objects.get_or_create(
        user=user,
        defaults={'display_name': display, 'lichess_username': lichess_username},
    )
    # Refresh in case it existed without these fields
    member.display_name = display
    member.lichess_username = lichess_username
    member.save(update_fields=['display_name', 'lichess_username'])
    return member


white = ensure_member('chayee333', 'chayee333', 'chayee333')
black = ensure_member('takudzwa25', 'takudzwa25', 'takudzwa25')

# --- Game ---------------------------------------------------------------------
PGN = """[Event "rated rapid game"]
[Site "https://lichess.org/2qSX5ngh"]
[Date "2026.05.14"]
[White "chayee333"]
[Black "takudzwa25"]
[Result "1-0"]
[GameId "2qSX5ngh"]
[UTCDate "2026.05.14"]
[UTCTime "09:59:36"]
[WhiteElo "1739"]
[BlackElo "1500"]
[Variant "Standard"]
[TimeControl "600+5"]
[ECO "C34"]
[Opening "King's Gambit Accepted: King's Knight's Gambit"]
[Termination "Normal"]

1. e4 e5 2. f4 exf4 3. Nf3 Bc5 4. Bc4 Nc6 5. d3 b6 6. Bxf4 h6 7. c3 Nce7
8. d4 Bd6 9. Ne5 Bb7 10. Nd2 Bc6 11. Nxf7 Kf8 12. Nxd8 Rxd8 13. Bxd6 Rc8
14. Qf3+ Ke8 15. Qf7+ Kd8 16. Bxe7+ Nxe7 17. Rf1 Bxe4 18. Qf8+ Rxf8 19. Rxf8# 1-0
"""

game, _ = Game.objects.update_or_create(
    lichess_game_id='2qSX5ngh',
    defaults={
        'player_white': white,
        'player_black': black,
        'pgn': PGN,
        'time_control': 'rapid',
        'result': '1-0',
        'played_at': datetime(2026, 5, 14, 9, 59, 36, tzinfo=timezone.utc),
    },
)

# --- GameAnalysis -------------------------------------------------------------
analysis, _ = GameAnalysis.objects.update_or_create(
    game=game,
    defaults={
        'status': 'completed',
        'depth': 20,
        'white_avg_centipawn_loss': 35.7,
        'black_avg_centipawn_loss': 48.3,
        'white_blunders': 1,
        'black_blunders': 2,
        'white_mistakes': 2,
        'black_mistakes': 5,
        'white_inaccuracies': 4,
        'black_inaccuracies': 3,
        'analysed_at': datetime(2026, 5, 14, 10, 5, 0, tzinfo=timezone.utc),
    },
)

# --- MoveEvaluations ----------------------------------------------------------
# (move_number, is_white, san, best_san, eval_before_cp, eval_after_cp, cpl, classification)
MOVES = [
    (1,  True,  'e4',    'e4',    0,    20,    0,   'best'),
    (1,  False, 'e5',    'e5',    20,   10,    0,   'best'),
    (2,  True,  'f4',    'Nf3',   10,   45,    30,  'inaccuracy'),
    (2,  False, 'exf4',  'exf4',  45,   30,    0,   'best'),
    (3,  True,  'Nf3',   'Nf3',   30,   30,    0,   'best'),
    (3,  False, 'Bc5',   'Be7',   30,   20,    35,  'inaccuracy'),
    (4,  True,  'Bc4',   'Bc4',   20,   40,    10,  'good'),
    (4,  False, 'Nc6',   'Nc6',   40,   30,    15,  'good'),
    (5,  True,  'd3',    'd4',    30,   35,    25,  'inaccuracy'),
    (5,  False, 'b6',    'd6',    35,   55,    55,  'mistake'),
    (6,  True,  'Bxf4',  'Bxf4',  55,   55,    5,   'best'),
    (6,  False, 'h6',    'Qf6',   55,   95,    95,  'mistake'),
    (7,  True,  'c3',    'd4',    95,   110,   30,  'inaccuracy'),
    (7,  False, 'Nce7',  'd5',    110,  180,   120, 'mistake'),
    (8,  True,  'd4',    'd4',    180,  220,   0,   'best'),
    (8,  False, 'Bd6',   'Bxf4',  220,  280,   70,  'mistake'),
    (9,  True,  'Ne5',   'Ne5',   280,  310,   5,   'best'),
    (9,  False, 'Bb7',   'd5',    310,  360,   55,  'mistake'),
    (10, True,  'Nd2',   'Nxf7',  360,  420,   80,  'mistake'),
    (10, False, 'Bc6',   'Bxe5',  420,  460,   75,  'mistake'),
    (11, True,  'Nxf7',  'Nxf7',  460,  520,   0,   'best'),
    (11, False, 'Kf8',   'Kxf7',  520,  950,   480, 'blunder'),
    (12, True,  'Nxd8',  'Nxd8',  950,  999,   0,   'best'),
    (12, False, 'Rxd8',  'Rxd8',  999,  999,   5,   'best'),
    (13, True,  'Bxd6',  'Bxd6',  999,  999,   0,   'best'),
    (13, False, 'Rc8',   'cxd6',  999,  999,   95,  'mistake'),
    (14, True,  'Qf3+',  'Qh5',   999,  999,   35,  'inaccuracy'),
    (14, False, 'Ke8',   'Nf6',   999,  999,   60,  'mistake'),
    (15, True,  'Qf7+',  'Qf7+',  999,  999,   0,   'best'),
    (15, False, 'Kd8',   'Kd8',   999,  999,   0,   'best'),
    (16, True,  'Bxe7+', 'Qf8#',  999,  999,   30,  'inaccuracy'),
    (16, False, 'Nxe7',  'Nxe7',  999,  999,   0,   'best'),
    (17, True,  'Rf1',   'Bxd6',  999,  999,   25,  'inaccuracy'),
    (17, False, 'Bxe4',  'd5',    999,  999,   180, 'blunder'),
    (18, True,  'Qf8+',  'Qf8+',  999,  999,   0,   'best'),
    (18, False, 'Rxf8',  'Rxf8',  999,  999,   0,   'best'),
    (19, True,  'Rxf8#', 'Rxf8#', 999,  999,   0,   'best'),
]

MoveEvaluation.objects.filter(analysis=analysis).delete()
for move_no, is_white, san, best, before, after, cpl, klass in MOVES:
    MoveEvaluation.objects.create(
        analysis=analysis,
        move_number=move_no,
        is_white=is_white,
        move_san=san,
        best_move_san=best,
        eval_before=before,
        eval_after=after,
        centipawn_loss=cpl,
        classification=klass,
    )

print(f"Seeded game {game.pk} (lichess id {game.lichess_game_id}) with "
      f"{MoveEvaluation.objects.filter(analysis=analysis).count()} move evaluations.")
print(f"Analysis URL: /ai_pipeline/games/{game.pk}/analysis/  "
      f"(or look up the actual URL in urls.py)")
