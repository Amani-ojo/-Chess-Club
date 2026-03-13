"""
ELO Rating Calculation Utilities

Uses the standard FIDE formula:
  Expected Score (E) = 1 / (1 + 10^((Rb - Ra) / 400))
  New Rating         = Ra + K * (S - E)
"""


def calculate_elo(ra, rb, score, k=20):
    """
    Calculate the new ELO rating for a player.

    ra    = current player's rating
    rb    = opponent's rating
    score = 1 (win), 0.5 (draw), 0 (loss)
    k     = K-factor (controls how fast ratings change)
    """
    expected = 1 / (1 + 10 ** ((rb - ra) / 400))
    new_rating = round(ra + k * (score - expected))
    return new_rating


def get_k_factor(member):
    """
    Determine the K-factor for a member based on their experience.

    K = 40 for new players (fewer than 30 games played)
    K = 10 for high-rated players (ELO above 2400)
    K = 20 for everyone else
    """
    total = member.wins + member.losses + member.draws
    if total < 30:
        return 40
    if member.elo_rating > 2400:
        return 10
    return 20
