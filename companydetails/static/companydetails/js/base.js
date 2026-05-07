// app.js - global custom JS for the site
// Place at: static/js/app.js
// Assumes Bootstrap 5 is already loaded (CSS + bundle JS)

// -----------------------------
// CSRF Helpers (Django-friendly)
// -----------------------------
function getCookie(name) {
    // classic Django cookie getter
    if (!document.cookie) return null;
    const cookies = document.cookie.split(';').map(c => c.trim());
    for (let cookie of cookies) {
        if (cookie.startsWith(name + '=')) {
            return decodeURIComponent(cookie.split('=')[1]);
        }
    }
    return null;
}
const csrftoken = getCookie('csrftoken');

function safeMethod(method) {
    return ['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method);
}

// -----------------------------
// Toast Notifications
// -----------------------------
// Minimal programmatic toast creator using Bootstrap's Toast component.
function showToast(message, { title = '', autohide = true, delay = 5000 } = {}) {
    // Ensure toast container exists
    let container = document.getElementById('global-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'global-toast-container';
        // place the container fixed at top-right
        container.style.position = 'fixed';
        container.style.top = '1rem';
        container.style.right = '1rem';
        container.style.zIndex = 1080; // above most content
        document.body.appendChild(container);
    }

    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toastEl = document.createElement('div');
    toastEl.className = 'toast';
    toastEl.id = toastId;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');

    toastEl.innerHTML = `
        <div class="toast-header">
            ${ title ? `<strong class="me-auto">${escapeHtml(title)}</strong>` : '<strong class="me-auto">Notice</strong>' }
            <small class="text-muted ms-2"></small>
            <button type="button" class="btn-close ms-2 mb-1" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">${escapeHtml(message)}</div>
    `;

    container.appendChild(toastEl);

    const bsToast = new bootstrap.Toast(toastEl, { autohide, delay });
    bsToast.show();

    // remove DOM element after hidden
    toastEl.addEventListener('hidden.bs.toast', () => {
        toastEl.remove();
    });

    return bsToast;
}

// simple HTML escape to avoid injecting HTML in messages
function escapeHtml(str) {
    if (typeof str !== 'string') return str;
    return str
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

// -----------------------------
// Fetch wrapper for API calls
// -----------------------------
async function apiFetch(url, options = {}) {
    // options: method, headers, body, showToastOnError (default true)
    const method = (options.method || 'GET').toUpperCase();
    const showToastOnError = options.showToastOnError ?? true;

    const headers = Object.assign({}, options.headers || {});
    // JSON default headers if body provided and not a FormData
    if (options.body && !(options.body instanceof FormData)) {
        headers['Content-Type'] = headers['Content-Type'] || 'application/json';
    }

    // Attach CSRF for unsafe methods
    if (!safeMethod(method)) {
        headers['X-CSRFToken'] = csrftoken;
    }

    const fetchOptions = {
        method,
        headers,
        credentials: 'same-origin', // include cookies
    };

    if (options.body) {
        fetchOptions.body = (options.body instanceof FormData) ? options.body : JSON.stringify(options.body);
    }

    try {
        const resp = await fetch(url, fetchOptions);
        const contentType = resp.headers.get('content-type') || '';
        let data = null;
        if (contentType.includes('application/json')) {
            data = await resp.json();
        } else {
            data = await resp.text();
        }

        if (!resp.ok) {
            // try to extract a friendly error message
            let errMsg = (data && data.detail) ? data.detail :
                         (data && data.error) ? data.error :
                         (typeof data === 'string' && data.length < 500) ? data :
                         `Request failed with status ${resp.status}`;
            if (showToastOnError) showToast(errMsg || `Error ${resp.status}`);
            const error = new Error(errMsg || `HTTP error ${resp.status}`);
            error.response = resp;
            error.data = data;
            throw error;
        }

        return data;
    } catch (err) {
        if (showToastOnError && !(err instanceof DOMException && err.name === 'AbortError')) {
            showToast(err.message || 'Network error');
        }
        throw err;
    }
}
// -----------------------------
// Confirm helpers
// -----------------------------
async function confirmAction({ title = 'Confirm', message = 'Are you sure?', confirmText = 'Yes', cancelText = 'Cancel' } = {}) {
    // Use window.confirm as a simple fallback
    return new Promise((resolve) => {
        if (typeof bootstrap === 'undefined') {
            // fallback
            const ok = window.confirm(`${title}\n\n${message}`);
            resolve(ok);
            return;
        }

        // Create modal on the fly
        const modalId = 'confirm-modal-' + Date.now();
        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
              <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                  <div class="modal-header">
                    <h5 class="modal-title">${escapeHtml(title)}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                  </div>
                  <div class="modal-body">${escapeHtml(message)}</div>
                  <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${escapeHtml(cancelText)}</button>
                    <button type="button" class="btn btn-primary" id="${modalId}-confirm">${escapeHtml(confirmText)}</button>
                  </div>
                </div>
              </div>
            </div>
        `;

        const wrapper = document.createElement('div');
        wrapper.innerHTML = modalHtml;
        document.body.appendChild(wrapper);

        const modalEl = document.getElementById(modalId);
        const bsModal = new bootstrap.Modal(modalEl, { backdrop: 'static' });
        bsModal.show();

        const cleanup = (result) => {
            bsModal.hide();
            // remove after hidden event to avoid DOM flicker
            modalEl.addEventListener('hidden.bs.modal', () => {
                wrapper.remove();
                resolve(result);
            }, { once: true });
        };

        modalEl.querySelector(`#${modalId}-confirm`).addEventListener('click', () => cleanup(true), { once: true });
        modalEl.querySelectorAll('[data-bs-dismiss="modal"]').forEach(btn => {
            btn.addEventListener('click', () => cleanup(false), { once: true });
        });
    });
}

// -----------------------------
// Utility helpers
// -----------------------------
function debounce(fn, wait = 250) {
    let t;
    return function(...args) {
        clearTimeout(t);
        t = setTimeout(() => fn.apply(this, args), wait);
    };
}

function initNavbarActive() {
    // Highlights navbar link matching the current path (basic)
    const path = window.location.pathname;
    document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
        // remove existing active
        link.classList.remove('active');
        try {
            const href = new URL(link.href);
            if (href.pathname === path) {
                link.classList.add('active');
            }
        } catch (e) {
            // fallback compare href string endsWith
            if (link.getAttribute('href') === path || link.href.endsWith(path)) {
                link.classList.add('active');
            }
        }
    });
}

function enableTooltips() {
    if (typeof bootstrap === 'undefined') return;
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (el) {
        return new bootstrap.Tooltip(el);
    });
}

// -----------------------------
// DOM Ready: initialize common UI stuff
// -----------------------------
document.addEventListener('DOMContentLoaded', function () {
    initNavbarActive();
    enableTooltips();

    // Example: auto attach confirm to elements with data-confirm attribute
    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', async function (evt) {
            // only intercept if element is not a link with target _blank and not disabled
            if (el.dataset.confirmHandled) return;
            const msg = el.getAttribute('data-confirm') || 'Are you sure?';
            const ok = await confirmAction({ message: msg });
            if (!ok) {
                evt.preventDefault();
                evt.stopImmediatePropagation();
            } else {
                // allow action (for links/forms, let normal flow continue)
            }
        }, { once: false });
    });

    // Example global fetch failure handler: log to console (optional)
    window.addEventListener('unhandledrejection', function (event) {
        console.warn('Unhandled promise rejection:', event.reason);
    });
});

// -----------------------------
// Expose some helpers globally so other scripts can use them
// -----------------------------
window.app = window.app || {};
Object.assign(window.app, {
    apiFetch,
    showToast,
    confirmAction,
    debounce,
    csrftoken,
    escapeHtml,
});

// -----------------------------
// End of file
// -----------------------------
