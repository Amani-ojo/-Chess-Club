import csv
import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from club.models import Member

from .models import Game


def _resolve_game(game_id):
    game_id = str(game_id).strip()
    query = Q(lichess_game_id=game_id)
    if game_id.isdigit():
        query = query | Q(pk=int(game_id))
    return get_object_or_404(Game, query)


def game_embed(request, game_id):
    game = _resolve_game(game_id)
    return render(request, 'ai_pipeline/game_embed.html', {'game': game})


def game_analysis_view(request, game_id):
    game = _resolve_game(game_id)
    analysis = getattr(game, 'analysis', None)
    moves = analysis.move_evaluations.all() if analysis else []
    report = None
    if analysis and analysis.status == 'completed':
        white_total = analysis.white_blunders + analysis.white_mistakes + analysis.white_inaccuracies
        black_total = analysis.black_blunders + analysis.black_mistakes + analysis.black_inaccuracies

        if (analysis.white_avg_centipawn_loss or 0) <= (analysis.black_avg_centipawn_loss or 0):
            stronger_side = 'White'
        else:
            stronger_side = 'Black'

        focus_areas = []
        if analysis.white_blunders or analysis.black_blunders:
            focus_areas.append('Reduce blunders by adding a final tactical scan before each move.')
        if analysis.white_mistakes or analysis.black_mistakes:
            focus_areas.append('Improve middlegame planning with candidate-move comparison.')
        if analysis.white_inaccuracies or analysis.black_inaccuracies:
            focus_areas.append('Sharpen opening move quality through pattern review and model lines.')
        if not focus_areas:
            focus_areas.append('Maintain consistency and deepen calculation in critical transitions.')

        report = {
            'stronger_side': stronger_side,
            'white_total_errors': white_total,
            'black_total_errors': black_total,
            'focus_areas': focus_areas,
            'summary': (
                f"Stockfish evaluated this game at depth {analysis.depth}. "
                f"{stronger_side} maintained the cleaner practical accuracy profile across the game."
            ),
        }
    return render(
        request,
        'ai_pipeline/game_analysis.html',
        {'game': game, 'analysis': analysis, 'moves': moves, 'report': report},
    )


def player_insights_view(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    insights = member.insights.all()
    return render(
        request,
        'ai_pipeline/player_insights.html',
        {'member': member, 'insights': insights},
    )


@login_required
def export_game_analysis(request, game_id, fmt='json'):
    game = _resolve_game(game_id)
    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.lichess_username:
        return HttpResponse('No linked member profile found.', status=403)
    username = profile.lichess_username.lower()
    allowed = (
        (game.player_white.lichess_username or '').lower() == username
        or (game.player_black.lichess_username or '').lower() == username
    )
    if not allowed:
        return HttpResponse('You are not allowed to export this analysis.', status=403)

    analysis = getattr(game, 'analysis', None)
    if not analysis:
        return HttpResponse('No analysis available for this game.', status=404)

    moves = analysis.move_evaluations.all().values(
        'move_number',
        'is_white',
        'move_san',
        'best_move_san',
        'eval_before',
        'eval_after',
        'centipawn_loss',
        'classification',
    )
    payload = {
        'game_id': game.id,
        'result': game.result,
        'time_control': game.time_control,
        'analysis_status': analysis.status,
        'white_avg_centipawn_loss': analysis.white_avg_centipawn_loss,
        'black_avg_centipawn_loss': analysis.black_avg_centipawn_loss,
        'moves': list(moves),
    }

    if fmt == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="game_{game.id}_analysis.csv"'
        writer = csv.writer(response)
        writer.writerow(['game_id', game.id])
        writer.writerow(['result', game.result])
        writer.writerow(['time_control', game.time_control])
        writer.writerow([])
        writer.writerow(['move_number', 'is_white', 'move_san', 'best_move_san', 'eval_before', 'eval_after', 'centipawn_loss', 'classification'])
        for move in payload['moves']:
            writer.writerow(
                [
                    move['move_number'],
                    move['is_white'],
                    move['move_san'],
                    move['best_move_san'],
                    move['eval_before'],
                    move['eval_after'],
                    move['centipawn_loss'],
                    move['classification'],
                ]
            )
        return response

    response = HttpResponse(json.dumps(payload, indent=2), content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="game_{game.id}_analysis.json"'
    return response
