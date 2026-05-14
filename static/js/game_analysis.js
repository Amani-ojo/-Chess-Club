/**
 * Full game analysis: link move table rows to move-by-move explanation cards.
 */
(function () {
    'use strict';

    function ready(fn) {
        if (document.readyState !== 'loading') fn();
        else document.addEventListener('DOMContentLoaded', fn);
    }

    ready(function () {
        const table = document.querySelector('.game-move-table');
        if (!table) return;

        let active = -1;

        function setActive(i, scrollTo) {
            active = i;
            table.querySelectorAll('tbody tr.analysis-move-row').forEach(function (row) {
                const idx = parseInt(row.getAttribute('data-move-index'), 10);
                row.classList.toggle('analysis-move-row-active', idx === i && i >= 0);
            });
            document.querySelectorAll('.analysis-move-detail-card').forEach(function (card) {
                const idx = parseInt(card.getAttribute('data-move-index'), 10);
                card.classList.toggle('analysis-move-detail-active', idx === i && i >= 0);
            });
            if (i < 0 || !scrollTo) return;
            if (scrollTo === 'detail') {
                const card = document.querySelector('.analysis-move-detail-card[data-move-index="' + i + '"]');
                if (card) card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else if (scrollTo === 'table') {
                const row = table.querySelector('tbody tr.analysis-move-row[data-move-index="' + i + '"]');
                if (row) row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }

        table.querySelectorAll('tbody tr.analysis-move-row').forEach(function (row) {
            row.addEventListener('click', function (e) {
                if (e.target.closest('a')) return;
                const i = parseInt(row.getAttribute('data-move-index'), 10);
                if (!Number.isFinite(i)) return;
                setActive(active === i ? -1 : i, active === i ? null : 'detail');
            });
        });

        document.querySelectorAll('.analysis-move-detail-card').forEach(function (card) {
            card.addEventListener('click', function () {
                const i = parseInt(card.getAttribute('data-move-index'), 10);
                if (!Number.isFinite(i)) return;
                setActive(active === i ? -1 : i, active === i ? null : 'table');
            });
        });
    });
})();
