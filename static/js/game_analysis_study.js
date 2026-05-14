/**
 * Study page: sync half-move index (m) with Lichess embed + engine line panel.
 * Index m matches the analysis move table / Board study links (0 = first row).
 */
(function () {
    'use strict';

    function ready(fn) {
        if (document.readyState !== 'loading') fn();
        else document.addEventListener('DOMContentLoaded', fn);
    }

    function readMeta() {
        const el = document.getElementById('study-moves-meta');
        if (!el) return [];
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
            console.warn('game_analysis_study: bad JSON', e);
            return [];
        }
    }

    ready(function () {
        const iframe = document.getElementById('studyLichessEmbed');
        const gameId = iframe && iframe.dataset ? iframe.dataset.lichessId : '';
        const meta = readMeta();
        if (!iframe || !gameId || !meta.length) return;

        let idx = 0;
        const params = new URLSearchParams(window.location.search);
        const qm = parseInt(params.get('m'), 10);
        if (Number.isFinite(qm) && qm >= 0 && qm < meta.length) {
            idx = qm;
        }

        const labelEl = document.getElementById('studyPositionLabel');
        const idxEl = document.getElementById('studyLineIndex');
        const playedEl = document.getElementById('studyLinePlayed');
        const bestEl = document.getElementById('studyLineBest');
        const evalEl = document.getElementById('studyLineEval');
        const cplEl = document.getElementById('studyLineCpl');

        function embedSrcForHalfMove(i) {
            // LPV reads initial ply from location.hash (see lila ui/site/src/site.lpvEmbed.ts).
            // Add a per-ply query param so each position is a distinct URL: fragments are not sent
            // on HTTP requests, so browsers/CDNs may reuse one cached embed HTML and ignore hash
            // changes — then the board never updates when you pick another explanation.
            const ply = Math.min(meta.length, Math.max(1, i + 1));
            const q = new URLSearchParams({ theme: 'auto', bg: 'auto', seek: String(ply) });
            return 'https://lichess.org/embed/game/' + encodeURIComponent(gameId) + '?' + q.toString() + '#' + ply;
        }

        function pushUrl() {
            const u = new URL(window.location.href);
            u.searchParams.set('m', String(idx));
            window.history.replaceState({}, '', u);
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
            const m = meta[idx];
            const side = m.white ? 'White' : 'Black';
            if (labelEl) {
                labelEl.textContent = 'Half-move ' + (idx + 1) + ' of ' + meta.length + ' — ' + side + ' to play ' +
                    (m.ply || '') + ' ' + (m.san || '');
            }
            if (idxEl) idxEl.textContent = String(idx) + ' (same as ?m= on the full report)';

            const played = (m.san || '—').trim() || '—';
            const bestRaw = (m.best || '').trim();
            const best = bestRaw && bestRaw !== played ? bestRaw : (bestRaw || '—');
            if (playedEl) playedEl.textContent = played;
            if (bestEl) {
                bestEl.textContent = best;
                bestEl.classList.toggle('text-success', !!(bestRaw && bestRaw !== played));
                bestEl.classList.toggle('text-muted', !bestRaw || bestRaw === played);
            }
            if (evalEl) {
                evalEl.textContent = (m.evalBefore || '—') + ' → ' + (m.evalAfter || '—');
            }
            if (cplEl) {
                cplEl.textContent = (m.cpl != null && Number.isFinite(Number(m.cpl))) ? Number(m.cpl).toFixed(1) : '—';
            }

            const nextSrc = embedSrcForHalfMove(idx);
            if (iframe.src !== nextSrc) {
                iframe.src = nextSrc;
            }
            pushUrl();
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

        document.querySelectorAll('.study-move-card').forEach((card) => {
            card.addEventListener('click', () => {
                const i = parseInt(card.getAttribute('data-move-index'), 10);
                if (Number.isFinite(i) && i >= 0 && i < meta.length) {
                    idx = i;
                    render();
                }
            });
        });

        render();
    });
})();
