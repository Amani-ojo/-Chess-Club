"""
Lichess API client — handles fetching games and creating challenges.

Docs: https://lichess.org/api
Rate limits: ~20 req/s with OAuth token, 1 req/s without.
"""

import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class LichessAPIError(Exception):
    """Raised when the Lichess API returns an unexpected response."""


class LichessClient:
    """Wrapper around the Lichess REST API."""

    def __init__(self):
        self.base_url = settings.LICHESS_API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {settings.LICHESS_API_TOKEN}',
        })

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path, params=None, accept='application/json'):
        """Issue a GET request and return the response."""
        self.session.headers['Accept'] = accept
        url = f'{self.base_url}{path}'
        response = self.session.get(url, params=params, timeout=30)
        if not response.ok:
            raise LichessAPIError(
                f'GET {url} returned {response.status_code}: {response.text[:200]}'
            )
        return response

    def _post(self, path, data=None):
        """Issue a POST request and return the parsed JSON body."""
        url = f'{self.base_url}{path}'
        response = self.session.post(url, data=data, timeout=30)
        if not response.ok:
            raise LichessAPIError(
                f'POST {url} returned {response.status_code}: {response.text[:200]}'
            )
        return response.json()

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def fetch_recent_games(self, lichess_username, max_games=20):
        """
        Fetch recent games for a Lichess user.

        GET /api/games/user/{username}

        Returns a list of game dicts. Each dict contains at minimum:
          'id', 'pgn', 'players' (white/black usernames), 'winner',
          'speed', 'createdAt'.
        """
        params = {
            'max': max_games,
            'pgnInJson': 'true',
            'moves': 'true',
            'clocks': 'false',
            'evals': 'false',
            'opening': 'false',
        }
        response = self._get(
            f'/games/user/{lichess_username}',
            params=params,
            accept='application/x-ndjson',
        )

        games = []
        for line in response.text.strip().splitlines():
            line = line.strip()
            if line:
                try:
                    games.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    logger.warning('Skipping malformed NDJSON line: %s — %s', line[:80], exc)

        logger.info('Fetched %d games for Lichess user "%s"', len(games), lichess_username)
        return games

    def fetch_game_pgn(self, game_id):
        """
        Fetch the PGN string for a specific Lichess game.

        GET /game/export/{gameId}

        Returns the raw PGN string.
        """
        response = self._get(
            f'/game/export/{game_id}',
            params={'moves': 'true', 'clocks': 'false', 'evals': 'false'},
            accept='application/x-chess-pgn',
        )
        pgn = response.text.strip()
        if not pgn:
            raise LichessAPIError(f'Empty PGN returned for game ID "{game_id}"')
        return pgn

    def create_challenge(self, lichess_username, time_limit=600, increment=5):
        """
        Send an open challenge to another Lichess user.

        POST /api/challenge/{username}

        Returns the challenge URL (str) that can be shared with the opponent.
        """
        data = {
            'clock.limit': time_limit,
            'clock.increment': increment,
            'color': 'random',
            'variant': 'standard',
        }
        result = self._post(f'/challenge/{lichess_username}', data=data)

        challenge_url = result.get('challenge', {}).get('url')
        if not challenge_url:
            raise LichessAPIError(
                f'Could not extract challenge URL from response: {result}'
            )

        logger.info('Challenge created for "%s": %s', lichess_username, challenge_url)
        return challenge_url
