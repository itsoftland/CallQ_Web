from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model

class CustomPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data.get('email')
        User = get_user_model()
        users = User.objects.filter(email__iexact=email, is_active=True)
        if not users.exists():
            raise forms.ValidationError("This email is not linked with any account.")
        
        # Explicit check for usable password to catch silent failures early
        if not any(u.has_usable_password() for u in users):
            raise forms.ValidationError("This account has no usable password set (e.g. social login or manual DB entry without hash). Please contact the administrator.")
            
        return email
