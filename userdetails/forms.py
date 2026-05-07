from django import forms
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm, UserChangeForm as BaseUserChangeForm
from .models import User

class UserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'company_relation', 'branch_relation')

class UserChangeForm(BaseUserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'company_relation', 'branch_relation')
