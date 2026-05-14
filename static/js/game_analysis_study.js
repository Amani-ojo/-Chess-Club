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

    /** Lichess embed routes use an 8-character game id. */
    function normalizeLichessGameId(raw) {
        const s = String(raw || '').trim();
        let m = s.match(/lichess\.org\/(?:embed\/)?(?:game\/)?([a-zA-Z0-9]{8})/i);
        if (m) return m[1];
        m = s.match(/^([a-zA-Z0-9]{8})$/);
        if (m) return m[1];
        return s;
    }

    function sameUrl(a, b) {
        if (!a || !b) return false;
        try {
            return new URL(a).href === new URL(b).href;
        } catch (e) {
            return a === b;
        }
    }

    ready(function () {
        const iframe = document.getElementById('studyLichessEmbed');
        const rawId = iframe && iframe.dataset ? iframe.dataset.lichessId : '';
        const gameId = normalizeLichessGameId(rawId);
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
            // LPV reads initial ply from location.hash (lila site.lpvEmbed.ts). Query must differ per ply
            // so the browser does not reuse one cached embed document for every # fragment.
            const ply = Math.min(meta.length, Math.max(1, i + 1));
            return (
                'https://lichess.org/embed/game/' +
                encodeURIComponent(gameId) +
                '?theme=auto&bg=auto&seek=' +
                ply +
                '#' +
                ply
            );
        }

        function pushUrl() {
            const u = new URL(window.location.href);
            u.searchParams.set('m', String(idx));
            window.history.replaceState({}, '', u);
        }

        function syncNarrative() {
            document.querySelectorAll('.study-move-card').forEach(function (c) {
                c.classList.remove('study-card-active');
            });
            const card = document.getElementById('study-card-' + idx);
            if (card) {
                card.classList.add('study-card-active');
                requestAnimationFrame(function () {
                    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                });
            }
        }

        function setStudyIframe(url) {
            if (sameUrl(iframe.src, url)) return;
            iframe.src = url;
        }

        function render() {
            const m = meta[idx];
            const side = m.white ? 'White' : 'Black';
            if (labelEl) {
                labelEl.textContent =
                    'Half-move ' +
                    (idx + 1) +
                    ' of ' +
                    meta.length +
                    ' — ' +
                    side +
                    ' to play ' +
                    (m.ply || '') +
                    ' ' +
                    (m.san || '');
            }
            if (idxEl) idxEl.textContent = String(idx) + ' (same as ?m= on the full report)';

            const played = (m.san || '—').trim() || '—';
            const bestRaw = (m.best || '').trim();
            const best = bestRaw && bestRaw !== played ? bestRaw : bestRaw || '—';
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
                cplEl.textContent =
                    m.cpl != null && Number.isFinite(Number(m.cpl)) ? Number(m.cpl).toFixed(1) : '—';
            }

            setStudyIframe(embedSrcForHalfMove(idx));
            pushUrl();
            syncNarrative();
        }

        document.getElementById('studyBtnPrev')?.addEventListener('click', function () {
            if (idx > 0) {
                idx -= 1;
                render();
            }
        });
        document.getElementById('studyBtnNext')?.addEventListener('click', function () {
            if (idx < meta.length - 1) {
                idx += 1;
                render();
            }
        });

        const narrative = document.getElementById('studyNarrativeColumn');
        if (narrative) {
            narrative.addEventListener('click', function (e) {
                const card = e.target.closest('.study-move-card');
                if (!card) return;
                const i = parseInt(card.getAttribute('data-move-index'), 10);
                if (Number.isFinite(i) && i >= 0 && i < meta.length) {
                    idx = i;
                    render();
                }
            });
        }

        render();
    });
})();
