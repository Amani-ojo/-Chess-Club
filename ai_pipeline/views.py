from django.shortcuts import render, get_object_or_404
from .models import Game, GameAnalysis, PlayerInsight
from club.models import Member


def game_embed(request, game_id):
    """Render the Lichess iframe embed for a game."""
    game = get_object_or_404(Game, pk=game_id)
    return render(request, 'ai_pipeline/game_embed.html', {'game': game})


def game_analysis_view(request, game_id):
    """Show Stockfish analysis results for a game."""
    game = get_object_or_404(Game, pk=game_id)
    analysis = getattr(game, 'analysis', None)
    moves = analysis.move_evaluations.all() if analysis else []
    return render(request, 'ai_pipeline/game_analysis.html', {
        'game': game,
        'analysis': analysis,
        'moves': moves,
    })


def player_insights_view(request, member_id):
    """Show aggregated insights for a club member."""
    member = get_object_or_404(Member, pk=member_id)
    insights = member.insights.all()
    return render(request, 'ai_pipeline/player_insights.html', {
        'member': member,
        'insights': insights,
    })
