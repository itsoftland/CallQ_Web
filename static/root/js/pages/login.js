document.addEventListener('DOMContentLoaded', function () {
    // Password visibility toggle
    var togglePassword = document.getElementById('togglePassword');
    var passwordInput = document.getElementById('passwordInput');
    var toggleIcon = document.getElementById('toggleIcon');

    if (togglePassword && passwordInput && toggleIcon) {
        togglePassword.addEventListener('click', function () {
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                toggleIcon.classList.remove('fa-eye');
                toggleIcon.classList.add('fa-eye-slash');
            } else {
                passwordInput.type = 'password';
                toggleIcon.classList.remove('fa-eye-slash');
                toggleIcon.classList.add('fa-eye');
            }
        });
    }
});
