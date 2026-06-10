document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const brandToggle = document.getElementById('brandToggle');

    // Sidebar is always open by default on every page load.
    // Only the logo click can collapse/expand it (no hover, no lock persistence).
    if (sidebar) {
        sidebar.classList.remove('collapsed', 'locked');
    }

    // Only the brand logo toggles the sidebar (minimise / restore)
    brandToggle?.addEventListener('click', function (e) {
        e.stopPropagation();
        if (!sidebar) return;
        sidebar.classList.toggle('collapsed');
    });

    // Mobile: always start collapsed on small screens
    if (window.innerWidth < 768 && sidebar) {
        sidebar.classList.add('collapsed');
    }

    // Auto-dismiss toasts after 5 seconds
    const toasts = document.querySelectorAll('.custom-toast');
    toasts.forEach(toast => {
        setTimeout(() => {
            closeToast(toast.id);
        }, 5000);
    });

    // Notification Dropdown Toggle
    const notificationBtn = document.getElementById('notificationBtn');
    const notificationDropdown = document.getElementById('notificationDropdown');

    notificationBtn?.addEventListener('click', function (e) {
        e.stopPropagation();
        notificationDropdown?.classList.toggle('show');
    });

    // Close dropdown on click outside
    document.addEventListener('click', function (e) {
        if (notificationDropdown && !notificationDropdown.contains(e.target) && !notificationBtn.contains(e.target)) {
            notificationDropdown.classList.remove('show');
        }
    });

    // Global Confirmation Modal Logic
    const confirmModalEl = document.getElementById('confirmModal');
    const confirmModal = confirmModalEl ? new bootstrap.Modal(confirmModalEl) : null;
    const confirmModalBtn = document.getElementById('confirmModalBtn');
    const confirmModalMessage = document.getElementById('confirmModalMessage');
    let pendingAction = null;

    document.addEventListener('click', function (e) {
        const confirmBtn = e.target.closest('[data-confirm]');
        if (confirmBtn) {
            e.preventDefault();
            const message = confirmBtn.getAttribute('data-confirm');
            if (confirmModalMessage) confirmModalMessage.textContent = message;

            pendingAction = () => {
                if (confirmBtn.tagName === 'A') {
                    window.location.href = confirmBtn.href;
                } else if (confirmBtn.type === 'submit' && confirmBtn.form) {
                    confirmBtn.form.submit();
                } else {
                    confirmBtn.click(); // Fallback
                }
            };

            confirmModal?.show();
        }
    });

    confirmModalBtn?.addEventListener('click', function () {
        if (pendingAction) {
            pendingAction();
            pendingAction = null;
            confirmModal?.hide();
        }
    });
});

/**
 * Closes a specific toast notification with animation
 * @param {string} toastId - The ID of the toast element
 */
function closeToast(toastId) {
    const toast = document.getElementById(toastId);
    if (toast) {
        toast.classList.add('hide');
        setTimeout(() => {
            toast.remove();
        }, 500); // Match animation duration
    }
}
