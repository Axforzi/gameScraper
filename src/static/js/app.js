/* gameScraper client behaviors (REQ-UI-5/9). Defer script, no imports.
   discountPercent/formatPrice mirror tests/test_price_math.py. Dynamic
   writes are textContent/createElement only (REQ-SEC-1, REQ-UI-9). */
(() => {
    'use strict';

    const TIMEOUT_MS = 65000;
    const $ = (selector, root = document) => root.querySelector(selector);
    const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

    /* --- price math (mirrored in tests/test_price_math.py) --- */
    function discountPercent(precio, descuento) {
        return precio > 0 && descuento != null
            ? Math.round(100 - (descuento * 100) / precio)
            : null;
    }

    function formatPrice(value, currency) {
        return `${Number(value).toFixed(2)} ${currency}`;
    }

    /* --- toast (504 partials show a visible error) --- */
    function showToast(message) {
        const toast = $('#toast');
        if (!toast) return;
        toast.textContent = message;
        toast.classList.add('is-visible');
        clearTimeout(showToast._timer);
        showToast._timer = setTimeout(() => toast.classList.remove('is-visible'), 4000);
    }

    /* --- results panel: open on submit, close via button/ESC/backdrop --- */
    const panel = $('#results-panel');
    const backdrop = $('#panel-backdrop');

    function openPanel() {
        if (!panel) return;
        panel.classList.add('is-open');
        backdrop?.classList.add('is-visible');
        panel.setAttribute('aria-hidden', 'false');
    }

    function closePanel() {
        if (!panel) return;
        panel.classList.remove('is-open');
        backdrop?.classList.remove('is-visible');
        panel.setAttribute('aria-hidden', 'true');
        $('#game')?.focus();
    }

    /* --- POST with X-CSRFToken from the meta tag and a 65s abort --- */
    async function fetchWithAbort(url, formData) {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': $('meta[name="csrf-token"]')?.content || '' },
                body: formData,
                signal: controller.signal,
            });
            let body = null;
            try {
                body = await response.json();
            } catch {
                /* non-JSON body: callers degrade to error states */
            }
            return { ok: response.ok, body };
        } finally {
            clearTimeout(timeout);
        }
    }

    /* --- DOM building blocks (no innerHTML with data) --- */
    function stateEl(className, message) {
        const element = document.createElement('p');
        element.className = className;
        element.textContent = message;
        return element;
    }

    function resetContainer(storeEl) {
        const container = $('.store-view, .offer-grid', storeEl) || storeEl;
        container.textContent = '';
        return container;
    }

    function showSkeleton(storeEl) {
        const skeleton = document.createElement('div');
        skeleton.className = 'skeleton';
        resetContainer(storeEl).appendChild(skeleton);
    }

    function renderError(storeEl, message) {
        resetContainer(storeEl).appendChild(
            stateEl('error-state', message || 'No se pudieron cargar los datos.')
        );
    }

    function fillCard(card, item, currency) {
        const img = $('.cover-img', card);
        if (img) {
            img.alt = item.nombre ? `Portada de ${item.nombre}` : '';
            img.src = item.img || img.dataset.placeholder; /* never "" */
            img.addEventListener('error', () => {
                img.src = img.dataset.placeholder;
            });
        }
        const titleEl = $('.card-title', card);
        if (titleEl) titleEl.textContent = item.nombre || '';
        const descEl = $('.card-desc', card);
        if (descEl) {
            descEl.textContent = item.descripcion || '';
            descEl.hidden = !item.descripcion;
        }
        const pct = discountPercent(item.precio, item.descuento);
        const originalEl = $('.price-original', card);
        const chipEl = $('.price-chip', card);
        const finalEl = $('.price-final', card);
        if (pct === null) {
            originalEl.hidden = chipEl.hidden = true;
            finalEl.textContent = formatPrice(item.precio, currency);
        } else {
            originalEl.textContent = formatPrice(item.precio, currency);
            chipEl.textContent = `-${pct}%`;
            finalEl.textContent = formatPrice(item.descuento, currency);
        }
        const linkEl = $('.card-link', card);
        if (linkEl) {
            linkEl.href = item.link || '#';
            linkEl.hidden = !item.link;
        }
    }

    /* --- render one [data-store] section: game object or offer list --- */
    function renderStore(storeEl, data, currency) {
        const container = resetContainer(storeEl);
        const items = Array.isArray(data) ? data : data ? [data] : [];
        if (!items.length) {
            container.appendChild(stateEl('empty-state', 'No hay resultados en esta tienda.'));
            return;
        }
        const template = $('#offer-card-template, #game-panel-template');
        if (!template) return;
        items.forEach((item) => {
            const card = template.content.cloneNode(true);
            fillCard(card, item, currency);
            container.appendChild(card);
        });
    }

    /* --- shared envelope handling: 200 renders; 400/502/504 degrade per
           store plus a toast; partial 504 keeps the available stores --- */
    function handlePayload(payload) {
        $$('[data-store]').forEach((store) => {
            const data = payload[store.dataset.store];
            if (payload.error && data == null) renderError(store, payload.error);
            else renderStore(store, data, payload.currency);
        });
        if (payload.error) showToast(payload.error);
    }

    async function runSearch(event) {
        event.preventDefault();
        openPanel();
        $$('[data-store]').forEach(showSkeleton);
        try {
            const result = await fetchWithAbort(event.currentTarget.action, new FormData(event.currentTarget));
            handlePayload(result.body || {});
        } catch {
            showToast('No se pudo completar la búsqueda.');
            $$('[data-store]').forEach((store) => renderError(store, 'No se pudo completar la búsqueda.'));
        }
    }

    async function loadOffers() {
        $$('[data-store]').forEach(showSkeleton);
        try {
            const result = await fetchWithAbort('/ofertas', new FormData());
            handlePayload(result.body || {});
        } catch {
            showToast('No se pudieron cargar las ofertas.');
            $$('[data-store]').forEach((store) => renderError(store, 'No se pudieron cargar las ofertas.'));
        }
    }

    /* --- init: feature-detected per page --- */
    $('#panel-close')?.addEventListener('click', closePanel);
    backdrop?.addEventListener('click', closePanel);
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') closePanel();
    });
    if ($('#game-form')) {
        $('#game-form').addEventListener('submit', runSearch);
    } else if ($('#offer-card-template')) {
        loadOffers();
    }
})();