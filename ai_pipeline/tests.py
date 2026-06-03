"""
Unit tests for the AI Pipeline app.

Run with:
    python manage.py test ai_pipeline --verbosity=2

These tests use mocks so NO Redis, NO Stockfish binary, and NO Lichess
connection is required. Everything external is simulated.
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from django.test import TestCase

# ──────────────────────────────────────────────────────────────────────────────
# 1.  stockfish_analysis  —  classify_move  &  analyse_game
# ──────────────────────────────────────────────────────────────────────────────

class TestClassifyMove(TestCase):
    """classify_move() maps centipawn loss to the correct label."""

    def setUp(self):
        from ai_pipeline.services.stockfish_analysis import classify_move
        self.classify = classify_move

    def test_best(self):
        self.assertEqual(self.classify(0), 'best')

    def test_excellent(self):
        self.assertEqual(self.classify(5), 'excellent')

    def test_good(self):
        self.assertEqual(self.classify(20), 'good')

    def test_inaccuracy(self):
        self.assertEqual(self.classify(40), 'inaccuracy')

    def test_mistake(self):
        self.assertEqual(self.classify(80), 'mistake')

    def test_blunder(self):
        self.assertEqual(self.classify(250), 'blunder')

    def test_boundary_excellent(self):
        self.assertEqual(self.classify(10), 'excellent')

    def test_boundary_blunder(self):
        self.assertEqual(self.classify(201), 'blunder')


class TestAnalyseGame(TestCase):
    """
    analyse_game() with a mocked Stockfish engine.

    We patch get_stockfish_engine() so the test never needs the binary.
    """

    SAMPLE_PGN = (
        "[Event \"Test\"]\n"
        "[White \"Alice\"]\n"
        "[Black \"Bob\"]\n"
        "[Result \"1-0\"]\n\n"
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 *"
    )

    def _make_engine(self, cp_value=30, blunder_on_white_move=False):
        """
        Return a mock Stockfish engine whose get_evaluation() always returns
        the same centipawn value so the mock never runs out of values.

        If blunder_on_white_move is True, alternate between a high positive
        eval and a large negative eval so that White's first move looks like
        a blunder.
        """
        engine = MagicMock()
        if blunder_on_white_move:
            # Even calls → +200 (before White's move), odd calls → -200 (after)
            call_count = {'n': 0}
            def alternating_eval():
                v = 200 if call_count['n'] % 2 == 0 else -200
                call_count['n'] += 1
                return {'type': 'cp', 'value': v}
            engine.get_evaluation.side_effect = alternating_eval
        else:
            engine.get_evaluation.return_value = {'type': 'cp', 'value': cp_value}
        engine.get_best_move.return_value = 'e2e4'
        return engine

    @patch('ai_pipeline.services.stockfish_analysis.get_stockfish_engine')
    def test_returns_move_list(self, mock_engine_factory):
        from ai_pipeline.services.stockfish_analysis import analyse_game

        mock_engine_factory.return_value = self._make_engine(cp_value=30)
        result = analyse_game(self.SAMPLE_PGN)

        self.assertIn('moves', result)
        self.assertEqual(len(result['moves']), 6)

    @patch('ai_pipeline.services.stockfish_analysis.get_stockfish_engine')
    def test_aggregate_keys_present(self, mock_engine_factory):
        from ai_pipeline.services.stockfish_analysis import analyse_game

        mock_engine_factory.return_value = self._make_engine(cp_value=0)
        result = analyse_game(self.SAMPLE_PGN)

        for key in ('white_avg_cpl', 'black_avg_cpl',
                    'white_blunders', 'black_blunders',
                    'white_mistakes', 'black_mistakes',
                    'white_inaccuracies', 'black_inaccuracies'):
            self.assertIn(key, result)

    @patch('ai_pipeline.services.stockfish_analysis.get_stockfish_engine')
    def test_blunder_counted(self, mock_engine_factory):
        from ai_pipeline.services.stockfish_analysis import analyse_game

        # Alternating +200/-200 means White's CPL on move 1 is 400 → blunder
        mock_engine_factory.return_value = self._make_engine(blunder_on_white_move=True)
        result = analyse_game(self.SAMPLE_PGN)

        self.assertGreaterEqual(result['white_blunders'], 1)

    @patch('ai_pipeline.services.stockfish_analysis.get_stockfish_engine')
    def test_invalid_pgn_returns_empty(self, mock_engine_factory):
        """
        python-chess does not raise an error for garbage input — it returns a
        game with no moves. analyse_game() should return zero moves and zero
        averages rather than crashing.
        """
        from ai_pipeline.services.stockfish_analysis import analyse_game

        mock_engine_factory.return_value = self._make_engine()
        result = analyse_game("this is not a pgn")

        self.assertEqual(result['moves'], [])
        self.assertEqual(result['white_avg_cpl'], 0.0)
        self.assertEqual(result['black_avg_cpl'], 0.0)

    @patch('ai_pipeline.services.stockfish_analysis.get_stockfish_engine')
    def test_mate_score_capped(self, mock_engine_factory):
        from ai_pipeline.services.stockfish_analysis import analyse_game, EVAL_CAP

        engine = MagicMock()
        # Return a forced-mate evaluation for every call
        engine.get_evaluation.return_value = {'type': 'mate', 'value': 3}
        engine.get_best_move.return_value = 'e2e4'
        mock_engine_factory.return_value = engine

        result = analyse_game(self.SAMPLE_PGN)

        for move in result['moves']:
            self.assertLessEqual(abs(move['eval_before']), EVAL_CAP)
            self.assertLessEqual(abs(move['eval_after']),  EVAL_CAP)


# ──────────────────────────────────────────────────────────────────────────────
# 2.  lichess_api  —  LichessClient
# ──────────────────────────────────────────────────────────────────────────────

class TestLichessClient(TestCase):
    """LichessClient methods with a mocked requests.Session."""

    def _make_client(self):
        from ai_pipeline.services.lichess_api import LichessClient
        with self.settings(
            LICHESS_API_BASE_URL='https://lichess.org/api',
            LICHESS_API_TOKEN='test-token',
        ):
            return LichessClient()

    # ---------- fetch_recent_games ----------

    @patch('ai_pipeline.services.lichess_api.requests.Session.get')
    def test_fetch_recent_games_parses_ndjson(self, mock_get):
        client = self._make_client()

        game1 = {'id': 'abc123', 'pgn': '1.e4 e5', 'players': {}, 'winner': 'white', 'speed': 'blitz', 'createdAt': 1700000000000}
        game2 = {'id': 'def456', 'pgn': '1.d4 d5', 'players': {}, 'winner': 'black', 'speed': 'rapid', 'createdAt': 1700001000000}

        mock_response        = MagicMock()
        mock_response.ok     = True
        mock_response.text   = json.dumps(game1) + '\n' + json.dumps(game2) + '\n'
        mock_get.return_value = mock_response

        with self.settings(
            LICHESS_API_BASE_URL='https://lichess.org/api',
            LICHESS_API_TOKEN='test-token',
        ):
            games = client.fetch_recent_games('testuser', max_games=2)

        self.assertEqual(len(games), 2)
        self.assertEqual(games[0]['id'], 'abc123')
        self.assertEqual(games[1]['id'], 'def456')

    @patch('ai_pipeline.services.lichess_api.requests.Session.get')
    def test_fetch_recent_games_api_error(self, mock_get):
        from ai_pipeline.services.lichess_api import LichessAPIError

        mock_response        = MagicMock()
        mock_response.ok     = False
        mock_response.status_code = 429
        mock_response.text   = 'Too Many Requests'
        mock_get.return_value = mock_response

        client = self._make_client()
        with self.settings(
            LICHESS_API_BASE_URL='https://lichess.org/api',
            LICHESS_API_TOKEN='test-token',
        ):
            with self.assertRaises(LichessAPIError):
                client.fetch_recent_games('testuser')

    # ---------- fetch_game_pgn ----------

    @patch('ai_pipeline.services.lichess_api.requests.Session.get')
    def test_fetch_game_pgn_returns_string(self, mock_get):
        mock_response        = MagicMock()
        mock_response.ok     = True
        mock_response.text   = '[Event "Test"]\n\n1.e4 e5 *'
        mock_get.return_value = mock_response

        client = self._make_client()
        with self.settings(
            LICHESS_API_BASE_URL='https://lichess.org/api',
            LICHESS_API_TOKEN='test-token',
        ):
            pgn = client.fetch_game_pgn('abc123')

        self.assertIn('1.e4', pgn)

    @patch('ai_pipeline.services.lichess_api.requests.Session.get')
    def test_fetch_game_pgn_empty_raises(self, mock_get):
        from ai_pipeline.services.lichess_api import LichessAPIError

        mock_response        = MagicMock()
        mock_response.ok     = True
        mock_response.text   = '   '
        mock_get.return_value = mock_response

        client = self._make_client()
        with self.settings(
            LICHESS_API_BASE_URL='https://lichess.org/api',
            LICHESS_API_TOKEN='test-token',
        ):
            with self.assertRaises(LichessAPIError):
                client.fetch_game_pgn('abc123')

    # ---------- create_challenge ----------

    @patch('ai_pipeline.services.lichess_api.requests.Session.post')
    def test_create_challenge_returns_url(self, mock_post):
        mock_response        = MagicMock()
        mock_response.ok     = True
        mock_response.json.return_value = {
            'challenge': {'url': 'https://lichess.org/challenge/xyz789'}
        }
        mock_post.return_value = mock_response

        client = self._make_client()
        with self.settings(
            LICHESS_API_BASE_URL='https://lichess.org/api',
            LICHESS_API_TOKEN='test-token',
        ):
            url = client.create_challenge('opponent')

        self.assertEqual(url, 'https://lichess.org/challenge/xyz789')

    @patch('ai_pipeline.services.lichess_api.requests.Session.post')
    def test_create_challenge_missing_url_raises(self, mock_post):
        from ai_pipeline.services.lichess_api import LichessAPIError

        mock_response        = MagicMock()
        mock_response.ok     = True
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        client = self._make_client()
        with self.settings(
            LICHESS_API_BASE_URL='https://lichess.org/api',
            LICHESS_API_TOKEN='test-token',
        ):
            with self.assertRaises(LichessAPIError):
                client.create_challenge('opponent')


# ──────────────────────────────────────────────────────────────────────────────
# 3.  insight_aggregator  —  phase helper & aggregate_insights
# ──────────────────────────────────────────────────────────────────────────────

class TestPhaseHelper(TestCase):
    def test_opening(self):
        from ai_pipeline.services.insight_aggregator import _phase
        self.assertEqual(_phase(1),  'opening')
        self.assertEqual(_phase(15), 'opening')

    def test_middlegame(self):
        from ai_pipeline.services.insight_aggregator import _phase
        self.assertEqual(_phase(16), 'middlegame')
        self.assertEqual(_phase(35), 'middlegame')

    def test_endgame(self):
        from ai_pipeline.services.insight_aggregator import _phase
        self.assertEqual(_phase(36), 'endgame')
        self.assertEqual(_phase(80), 'endgame')
