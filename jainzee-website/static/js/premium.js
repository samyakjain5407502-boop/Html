// ==================== JAINZEE PREMIUM UX LAYER ====================
// Shared enhancements loaded on every page BEFORE main.js / admin.js:
//   * JZ.swrFetch  - SWR-style API cache: serve stale data instantly,
//                    revalidate in the background (no laggy page navigations)
//   * JZ.mutate    - cache invalidation after a mutation (POST/PUT/DELETE)
//   * JZ.toast     - animated toast notifications (icons, stacking, easing)
//   * JZ.skeleton* - shimmering skeleton loader markup builders
//   * JZ.btnBusy   - optimistic button spinner/disabled state
//   * JZ.pop       - micro pop animation (cart badge, wishlist heart)
//   * Motion       - page enter/leave transitions + tap feedback
//   * JZ.enhanceImages - lazy loading + fade-in + error fallback for <img>
//
// No build step, no dependencies - vanilla JS mirroring the SWR /
// React-Query "stale-while-revalidate" model used by premium SPAs.
(function () {
    'use strict';

    // ---------------- API CACHE (SWR / React-Query style) ----------------

    var mem = new Map();      // url -> { data, ts }
    var inflight = new Map(); // url -> Promise (dedupes concurrent requests)
    var SS_PREFIX = 'jz:swr:';

    function ssRead(url) {
        try {
            var raw = sessionStorage.getItem(SS_PREFIX + url);
            return raw ? JSON.parse(raw) : null;
        } catch (e) { return null; }
    }

    function ssWrite(url, entry) {
        try {
            sessionStorage.setItem(SS_PREFIX + url, JSON.stringify(entry));
        } catch (e) { /* quota / private mode - memory cache still works */ }
    }

    function ssDelete(url) {
        try { sessionStorage.removeItem(SS_PREFIX + url); } catch (e) {}
    }

    function readEntry(url, persist) {
        var entry = mem.get(url);
        if (entry) return entry;
        if (persist) {
            entry = ssRead(url);
            if (entry && typeof entry.ts === 'number' && entry.data !== undefined) {
                mem.set(url, entry);
                return entry;
            }
        }
        return null;
    }

    function writeEntry(url, data, persist) {
        var entry = { data: data, ts: Date.now() };
        mem.set(url, entry);
        if (persist) ssWrite(url, entry);
        return entry;
    }

    function fetchJSON(url) {
        return fetch(url, { credentials: 'same-origin' }).then(function (res) {
            if (!res.ok) {
                var err = new Error('HTTP ' + res.status);
                err.status = res.status;
                throw err;
            }
            return res.json();
        });
    }

    function revalidate(url, persist) {
        var p = inflight.get(url);
        if (p) return p;
        p = fetchJSON(url).then(function (data) {
            writeEntry(url, data, persist);
            return data;
        }).finally(function () { inflight.delete(url); });
        inflight.set(url, p);
        return p;
    }

    // The core SWR contract:
    //   fresh cache  -> resolves instantly (no network)
    //   stale cache  -> resolves instantly with stale data AND revalidates in
    //                   the background, calling opts.onUpdate(freshData) later
    //   cold         -> awaits the network
    function swrFetch(url, opts) {
        opts = opts || {};
        var staleTime = typeof opts.staleTime === 'number' ? opts.staleTime : 60000;
        var persist = !!opts.persist;
        var entry = readEntry(url, persist);
        var now = Date.now();

        if (entry && (now - entry.ts) < staleTime) {
            return Promise.resolve(entry.data);
        }
        if (entry) {
            revalidate(url, persist).then(function (data) {
                if (typeof opts.onUpdate === 'function') {
                    try { opts.onUpdate(data); } catch (e) { console.error('SWR onUpdate failed:', e); }
                }
            }).catch(function () { /* background refresh failed - keep stale data */ });
            return Promise.resolve(entry.data);
        }
        return revalidate(url, persist);
    }

    // Synchronous cache peek (null when nothing is cached / not fresh).
    function peek(url, opts) {
        opts = opts || {};
        var entry = readEntry(url, !!opts.persist);
        if (!entry) return null;
        if (opts.allowStale) return entry.data;
        var staleTime = typeof opts.staleTime === 'number' ? opts.staleTime : 60000;
        return (Date.now() - entry.ts) < staleTime ? entry.data : null;
    }

    // Populate the cache directly (e.g. after a manual fetch/poll).
    function set(url, data, opts) {
        return writeEntry(url, data, !!(opts && opts.persist));
    }

    // Invalidate after a mutation so the next read re-fetches.
    function mutate(url) {
        mem.delete(url);
        ssDelete(url);
    }

    // Invalidate every cached URL under a prefix (mutateAll('/admin/api/products')).
    function mutateAll(prefix) {
        Array.from(mem.keys()).forEach(function (k) {
            if (!prefix || k.indexOf(prefix) === 0) mutate(k);
        });
    }

    // ---------------- SKELETON LOADER BUILDERS ----------------

    // Product-card shaped skeletons for the public storefront grid.
    function skeletonCards(count) {
        count = count || 6;
        var html = '';
        for (var i = 0; i < count; i++) {
            html += '<div class="skeleton-card" aria-hidden="true">' +
                '<div class="sk-block sk-image"></div>' +
                '<div class="sk-block sk-line w70"></div>' +
                '<div class="sk-block sk-line w45" style="width:45%"></div>' +
                '<div class="sk-block sk-line w90"></div>' +
                '<div class="sk-block sk-line w60"></div>' +
                '<div class="sk-row"><div class="sk-block"></div><div class="sk-block"></div><div class="sk-block"></div></div>' +
                '<div class="sk-block sk-cta"></div>' +
            '</div>';
        }
        return html;
    }

    // Table-row skeletons for admin tables (products, orders, coupons).
    function skeletonRows(rows, cols) {
        rows = rows || 6;
        cols = cols || 6;
        var html = '';
        for (var r = 0; r < rows; r++) {
            html += '<tr class="skeleton-row" aria-hidden="true">';
            for (var c = 0; c < cols; c++) {
                html += '<td>' + (c === 0
                    ? '<div class="sk-block sk-thumb"></div>'
                    : '<div class="sk-block sk-line w80"></div>') + '</td>';
            }
            html += '</tr>';
        }
        return html;
    }

    // Simple line skeletons for lists / dashboard panels.
    function skeletonLines(count) {
        count = count || 4;
        var widths = ['w90', 'w70', 'w80', 'w50', 'w60', 'w70'];
        var html = '<div class="sk-list" aria-hidden="true">';
        for (var i = 0; i < count; i++) {
            html += '<div class="sk-block sk-line ' + widths[i % widths.length] + '"></div>';
        }
        return html + '</div>';
    }

    // ---------------- TOAST NOTIFICATIONS ----------------

    var TOAST_ICONS = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warn: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };

    function toast(message, type) {
        type = type || 'success';
        var container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        // Cap the stack so a burst of errors cannot cover the screen.
        var existing = container.querySelectorAll('.jz-toast');
        if (existing.length >= 4) existing[0].remove();

        var el = document.createElement('div');
        el.className = 'toast jz-toast ' + type;
        el.setAttribute('role', 'status');

        var icon = document.createElement('i');
        icon.className = 'fas ' + (TOAST_ICONS[type] || TOAST_ICONS.success) + ' jz-toast-icon';
        icon.setAttribute('aria-hidden', 'true');

        var text = document.createElement('span');
        text.className = 'jz-toast-text';
        text.textContent = String(message == null ? '' : message); // XSS-safe

        el.appendChild(icon);
        el.appendChild(text);
        container.appendChild(el);

        var ttl = (type === 'error') ? 4500 : 3200;
        setTimeout(function () {
            el.classList.add('jz-toast-out');
            setTimeout(function () { el.remove(); }, 320);
        }, ttl);
    }

    // ---------------- BUTTON BUSY STATE (optimistic UI) ----------------

    function btnBusy(btn, busy) {
        if (!btn) return;
        if (busy) {
            if (btn.classList.contains('is-loading')) return;
            btn.classList.add('is-loading');
            btn.dataset.jzWasDisabled = btn.disabled ? '1' : '0';
            if ('disabled' in btn) btn.disabled = true;
            btn.setAttribute('aria-busy', 'true');
        } else {
            btn.classList.remove('is-loading');
            if ('disabled' in btn) btn.disabled = (btn.dataset.jzWasDisabled === '1');
            delete btn.dataset.jzWasDisabled;
            btn.removeAttribute('aria-busy');
        }
    }

    // Trigger the pop micro-animation (cart badge, wishlist heart, ...).
    function pop(el) {
        if (!el) return;
        el.classList.remove('jz-pop');
        void el.offsetWidth; // restart the animation
        el.classList.add('jz-pop');
    }

    // ---------------- OPTIMIZED IMAGES ----------------
    // Lazy loading + fade-in + graceful error fallback for every <img>.

    function enhanceImage(img) {
        if (!img || img.dataset.jzEnhanced) return;
        img.dataset.jzEnhanced = '1';

        // Keep above-the-fold brand imagery eager (LCP); lazy-load the rest.
        var eager = img.hasAttribute('data-eager') ||
            !!(img.closest && img.closest('.navbar, header, .hero-content, .lang-toggle'));
        if (!eager) img.setAttribute('loading', 'lazy');
        img.setAttribute('decoding', 'async');

        if (img.hasAttribute('data-no-fade')) return;
        img.classList.add('jz-img');
        if (img.complete) {
            if (img.naturalWidth > 0) img.classList.add('jz-img-loaded');
            else img.classList.add('jz-img-error');
        }
    }

    function enhanceImages(root) {
        var scope = root || document;
        if (!scope) return;
        if (scope.nodeType === 1 && scope.tagName === 'IMG') enhanceImage(scope);
        if (scope.querySelectorAll) {
            scope.querySelectorAll('img').forEach(enhanceImage);
        }
    }

    // load/error don't bubble, so use capture to catch every image.
    document.addEventListener('load', function (e) {
        var t = e.target;
        if (t && t.tagName === 'IMG') {
            enhanceImage(t);
            t.classList.remove('jz-img-error');
            t.classList.add('jz-img-loaded');
        }
    }, true);

    document.addEventListener('error', function (e) {
        var t = e.target;
        if (t && t.tagName === 'IMG') {
            enhanceImage(t);
            t.classList.add('jz-img-error');
        }
    }, true);

    // ---------------- PAGE MOTION ----------------

    var REDUCED_MOTION = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

    function initMotion() {
        if (REDUCED_MOTION) return;

        // Entrance animation for the page itself.
        document.body.classList.add('jz-enter');
        setTimeout(function () { document.body.classList.remove('jz-enter'); }, 600);

        // Exit animation for same-origin link navigations, then navigate.
        document.addEventListener('click', function (e) {
            if (e.defaultPrevented || e.button !== 0 ||
                e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
            var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
            if (!a) return;
            if (a.target === '_blank' || a.hasAttribute('download') ||
                a.dataset.noTransition !== undefined) return;
            var href = a.getAttribute('href') || '';
            if (href.charAt(0) === '#' || href.indexOf('mailto:') === 0 ||
                href.indexOf('tel:') === 0 || href.indexOf('javascript:') === 0) return;
            var url;
            try { url = new URL(href, location.href); } catch (err) { return; }
            if (url.origin !== location.origin) return;
            if (url.pathname === location.pathname && url.search === location.search) return;

            e.preventDefault();
            document.body.classList.add('jz-leaving');
            setTimeout(function () { window.location.href = url.href; }, 160);
        });

        // Back/forward cache restores: cancel the exit state, replay entrance.
        window.addEventListener('pageshow', function (e) {
            document.body.classList.remove('jz-leaving');
            if (e.persisted) {
                document.body.classList.add('jz-enter');
                setTimeout(function () { document.body.classList.remove('jz-enter'); }, 600);
            }
        });
    }

    // ---------------- INIT ----------------

    document.addEventListener('DOMContentLoaded', function () {
        enhanceImages(document);
        initMotion();

        // Auto-enhance images injected later (product grids, media, admin...).
        if (window.MutationObserver && document.body) {
            new MutationObserver(function (mutations) {
                mutations.forEach(function (m) {
                    m.addedNodes && Array.prototype.forEach.call(m.addedNodes, function (n) {
                        if (n.nodeType === 1) enhanceImages(n);
                    });
                });
            }).observe(document.body, { childList: true, subtree: true });
        }
    });

    // ---------------- PUBLIC API ----------------

    window.JZ = {
        swrFetch: swrFetch,
        peek: peek,
        set: set,
        mutate: mutate,
        mutateAll: mutateAll,
        toast: toast,
        btnBusy: btnBusy,
        pop: pop,
        skeletonCards: skeletonCards,
        skeletonRows: skeletonRows,
        skeletonLines: skeletonLines,
        enhanceImages: enhanceImages,
        reducedMotion: REDUCED_MOTION
    };
})();


