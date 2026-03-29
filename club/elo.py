"""
ELO Rating Engine for the Eschen Chess Club.

Uses the FIDE rating formula with adaptive K-factor:
  K = 40  → new players (fewer than 30 games)
  K = 20  → standard players
  K = 10  → elite players (ELO ≥ 2400)
"""

from __future__ import annotations

from typing import NamedTuple


class EloResult(NamedTuple):
    """Immutable container for a pair of updated ratings."""
    white_new: int
    black_new: int


def k_factor(elo: int, total_games: int) -> int:
    """Return the adaptive K-factor for a player."""
    if total_games < 30:
        return 40
    if elo >= 2400:
        return 10
    return 20


def expected_score(rating_a: int, rating_b: int) -> float:
    """FIDE expected-score formula: E_A = 1 / (1 + 10^((R_B - R_A) / 400))."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def calculate_elo(
    white_elo: int,
    black_elo: int,
    white_games: int,
    black_games: int,
    result: str,
) -> EloResult:
    """
    Calculate new ELO ratings after a match.

    Parameters
    ----------
    white_elo : current rating of the white player
    black_elo : current rating of the black player
    white_games : total games played by white (for K-factor)
    black_games : total games played by black (for K-factor)
    result : one of 'white_wins', 'black_wins', 'draw'

    Returns
    -------
    EloResult with the new integer ratings for both players.
    """
    score_map = {
        "white_wins": (1.0, 0.0),
        "black_wins": (0.0, 1.0),
        "draw": (0.5, 0.5),
    }

    if result not in score_map:
        raise ValueError(f"Invalid result: {result!r}")

    white_score, black_score = score_map[result]

    white_expected = expected_score(white_elo, black_elo)
    black_expected = expected_score(black_elo, white_elo)

    k_white = k_factor(white_elo, white_games)
    k_black = k_factor(black_elo, black_games)

    white_new = round(white_elo + k_white * (white_score - white_expected))
    black_new = round(black_elo + k_black * (black_score - black_expected))

    return EloResult(white_new=white_new, black_new=black_new)
