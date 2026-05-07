// CSRF Token Helper
function getCSRFToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.startsWith(name + '=')) {
            return cookie.substring(name.length + 1);
        }
    }
    return '';
}

// Show Alert
function showAlert(message, type = 'danger') {
    const alertContainer = document.getElementById('alertContainer');
    if (alertContainer) {
        alertContainer.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    // Toggle Password Visibility
    const togglePassword = document.getElementById('togglePassword');
    if (togglePassword) {
        togglePassword.addEventListener('click', function () {
            const passwordInput = document.getElementById('password');
            const icon = this.querySelector('i');

            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                passwordInput.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    }

    // Role-based redirect configuration
    const ROLE_REDIRECTS = {
        'admin': '/admin/dashboard/',
        'superadmin': '/admin/dashboard/',
        'user': '/user/dashboard/',
        'customer': '/customer-list/',
        'staff': '/staff/dashboard/',
        'employee': '/employee/dashboard/'
    };

    // Form Submission
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            const rememberMe = document.getElementById('rememberMe').checked;
            const loginBtn = document.getElementById('loginBtn');

            // Disable button and show loading
            loginBtn.disabled = true;
            loginBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Signing in...';

            try {
                // Call Django login API
                const response = await fetch('/api/login/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    },
                    body: JSON.stringify({
                        username: username,
                        password: password
                    })
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || data.message || 'Login failed');
                }

                // Store authentication token/session
                if (data.token) {
                    localStorage.setItem('authToken', data.token);
                }

                // Store user info based on remember me
                const userInfo = {
                    username: data.user?.username || username,
                    role: data.user?.role || data.role,
                    name: data.user?.name || data.name || username
                };

                if (rememberMe) {
                    localStorage.setItem('user', JSON.stringify(userInfo));
                } else {
                    sessionStorage.setItem('user', JSON.stringify(userInfo));
                }

                showAlert(`Welcome back, ${userInfo.name}! Redirecting...`, 'success');

                // Get redirect URL based on user role
                const userRole = userInfo.role.toLowerCase();
                const redirectUrl = ROLE_REDIRECTS[userRole] || '/dashboard/';

                // Redirect after short delay
                setTimeout(() => {
                    window.location.href = redirectUrl;
                }, 1000);

            } catch (error) {
                console.error('Login error:', error);
                showAlert(error.message || 'Login failed. Please check your credentials.', 'danger');
            } finally {
                // Re-enable button
                loginBtn.disabled = false;
                loginBtn.innerHTML = '<i class="fas fa-sign-in-alt me-2"></i>Sign In';
            }
        });
    }

    // Check if user is already logged in
    const user = JSON.parse(localStorage.getItem('user') || sessionStorage.getItem('user') || 'null');

    if (user && user.role) {
        // User is already logged in, redirect to appropriate dashboard
        const ROLE_REDIRECTS_INTERNAL = {
            'admin': '/admin/dashboard/',
            'superadmin': '/admin/dashboard/',
            'user': '/user/dashboard/',
            'customer': '/customer-list/',
            'staff': '/staff/dashboard/',
            'employee': '/employee/dashboard/'
        };
        const redirectUrl = ROLE_REDIRECTS_INTERNAL[user.role.toLowerCase()] || '/dashboard/';
        // window.location.href = redirectUrl; // Disabled to prevent accidental loops during dev
    }

    // Prevent back button after logout
    window.addEventListener('pageshow', function (event) {
        if (event.persisted) {
            window.location.reload();
        }
    });
});
