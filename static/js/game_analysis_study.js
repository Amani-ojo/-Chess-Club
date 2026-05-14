/**
 * Interactive study board: position before each half-move, compare played vs engine best.
 */
(function () {
    'use strict';

    function ready(fn) {
        if (document.readyState !== 'loading') fn();
        else document.addEventListener('DOMContentLoaded', fn);
    }

    function readMeta() {
        const el = document.getElementById('study-moves-meta');
        const pgnEl = document.getElementById('ai-pgn-source');
        if (!el) return null;
        try {
            return {
                moves: JSON.parse(el.textContent),
                pgn: pgnEl ? pgnEl.textContent.trim() : ''
            };
        } catch (e) {
            console.warn('game_analysis_study: bad JSON', e);
            return null;
        }
    }

    function fenSequenceFromPgn(pgn) {
        const fens = [];
        const replay = new Chess();
        fens.push(replay.fen());
        if (!pgn) return fens;
        const loader = new Chess();
        let history;
        try {
            if (!loader.load_pgn(pgn, { sloppy: true })) return fens;
            history = loader.history({ verbose: true });
        } catch (e) {
            return fens;
        }
        for (const move of history) {
            replay.move(move);
            fens.push(replay.fen());
        }
        return fens;
    }

    function sanToSquares(fen, san) {
        try {
            const c = new Chess(fen);
            const mv = c.move(san, { sloppy: true });
            return mv ? { from: mv.from, to: mv.to } : null;
        } catch (e) {
            return null;
        }
    }

    function clearHighlights(boardId) {
        $('#' + boardId + ' [class^="square-"]').removeClass(
            'study-hl-played-from study-hl-played-to study-hl-best-from study-hl-best-to'
        );
    }

    ready(function () {
        if (typeof Chess === 'undefined' || typeof Chessboard === 'undefined') return;
        const data = readMeta();
        if (!data || !data.moves.length) return;

        const fens = fenSequenceFromPgn(data.pgn);
        const boardId = 'studyBoard';
        let idx = 0;

        const params = new URLSearchParams(window.location.search);
        const qm = parseInt(params.get('m'), 10);
        if (Number.isFinite(qm) && qm >= 0 && qm < data.moves.length) {
            idx = qm;
        }

        const meta = data.moves;
        const labelEl = document.getElementById('studyPositionLabel');
        const hintEl = document.getElementById('studyToggleHint');
        const showPlayed = document.getElementById('studyShowPlayed');
        const showBest = document.getElementById('studyShowBest');

        const board = Chessboard(boardId, {
            position: fens[0] || 'start',
            draggable: false,
            pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
            showNotation: true,
        });

        function currentFen() {
            return fens[idx] || fens[0] || 'start';
        }

        function currentMove() {
            return meta[idx] || meta[0];
        }

        function updateToggleUi() {
            const m = currentMove();
            const best = (m.best || '').trim();
            const same = !best || best === m.san;
            const wrap = document.getElementById('studyToggleWrap');
            if (wrap) {
                wrap.style.display = same ? 'none' : '';
            }
            if (hintEl) {
                hintEl.textContent = same
                    ? 'Engine matches the played move — highlights show that continuation.'
                    : 'Red: played move from this position. Green: engine’s strongest alternative.';
            }
            if (same && showPlayed) {
                showPlayed.checked = true;
            }
        }

        function applyHighlights() {
            clearHighlights(boardId);
            const fen = currentFen();
            const m = currentMove();
            const played = sanToSquares(fen, m.san);
            const bestSan = (m.best || '').trim();
            const best = bestSan && bestSan !== m.san ? sanToSquares(fen, bestSan) : null;
            const preferEngine = showBest && showBest.checked && best;

            setTimeout(() => {
                if (preferEngine && best) {
                    $('#' + boardId + ' .square-' + best.from).addClass('study-hl-best-from');
                    $('#' + boardId + ' .square-' + best.to).addClass('study-hl-best-to');
                } else if (played) {
                    $('#' + boardId + ' .square-' + played.from).addClass('study-hl-played-from');
                    $('#' + boardId + ' .square-' + played.to).addClass('study-hl-played-to');
                }
            }, 60);
        }

        function syncNarrative() {
            document.querySelectorAll('.study-move-card').forEach((c) => c.classList.remove('study-card-active'));
            const card = document.getElementById('study-card-' + idx);
            if (card) {
                card.classList.add('study-card-active');
                card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }

        function render() {
            const fen = currentFen();
            const m = currentMove();
            const side = m.white ? 'White' : 'Black';
            board.orientation(m.white ? 'white' : 'black');
            board.position(fen);
            if (labelEl) {
                labelEl.textContent = 'Position before ' + side + "'s " + (m.ply || '') + ' ' + (m.san || '') +
                    ' (half-move ' + (idx + 1) + ' of ' + meta.length + ')';
            }
            updateToggleUi();
            applyHighlights();
            syncNarrative();
        }

        document.getElementById('studyBtnPrev')?.addEventListener('click', () => {
            if (idx > 0) {
                idx -= 1;
                render();
            }
        });
        document.getElementById('studyBtnNext')?.addEventListener('click', () => {
            if (idx < meta.length - 1) {
                idx += 1;
                render();
            }
        });

        showPlayed?.addEventListener('change', () => { if (showPlayed.checked) applyHighlights(); });
        showBest?.addEventListener('change', () => { if (showBest.checked) applyHighlights(); });

        document.querySelectorAll('.study-move-card').forEach((card) => {
            card.addEventListener('click', () => {
                const i = parseInt(card.getAttribute('data-move-index'), 10);
                if (Number.isFinite(i)) {
                    idx = i;
                    render();
                }
            });
        });

        render();
    });
})();
