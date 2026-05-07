from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class EmailOrUsernameBackend(ModelBackend):
    """
    Custom authentication backend to allow login using either 
    username or email.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        
        try:
            # Check for username OR email matches
            user = User.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            # Fallback to email if multiple users found (should be unique but good practice)
            user = User.objects.filter(email__iexact=username).first()
        
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
