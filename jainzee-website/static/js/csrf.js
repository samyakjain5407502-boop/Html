// ==================== CSRF PROTECTION HELPER ====================
// Automatically attaches the CSRF token cookie to every same-origin fetch
// as the X-CSRF-TOKEN header. Required for all POST/PUT/DELETE requests.
(function () {
    function getCookie(name) {
        const parts = document.cookie.split(';');
        for (let i = 0; i < parts.length; i++) {
            const kv = parts[i].trim();
            const eq = kv.indexOf('=');
            if (eq > -1 && kv.substring(0, eq) === name) {
                return decodeURIComponent(kv.substring(eq + 1));
            }
        }
        return '';
    }

    const originalFetch = window.fetch;
    window.fetch = function (input, init) {
        try {
            init = init || {};
            const url = typeof input === 'string' ? input : (input && input.url) || '';
            const method = ((init && init.method) || (input && input.method) || 'GET').toUpperCase();
            if (method !== 'GET' && url.indexOf('/') === 0) {
                let headers = init.headers;
                if (!headers || typeof headers.append !== 'function') {
                    headers = new Headers(headers || {});
                }
                if (!headers.has('X-CSRF-TOKEN')) {
                    headers.set('X-CSRF-TOKEN', getCookie('csrf_token'));
                }
                init.headers = headers;
            }
        } catch (e) {
            // Never break the app because of the CSRF wrapper
        }
        return originalFetch.call(this, input, init);
    };
})();
