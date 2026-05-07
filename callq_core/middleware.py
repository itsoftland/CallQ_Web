import traceback
import json
import logging
from django.http import JsonResponse
from django.db import IntegrityError
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import resolve, reverse
from django.conf import settings

logger = logging.getLogger('actions')

class GlobalExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            return self.process_exception(request, e)

    def process_exception(self, request, exception):
        # Log the exception
        logger.error(f"Global Exception Caught: {str(exception)}")
        logger.error(traceback.format_exc())

        user_message = "An unexpected error occurred. Please try again."

        if isinstance(exception, IntegrityError):
            error_msg = str(exception).lower()
            if "duplicate entry" in error_msg:
                if "username" in error_msg:
                    user_message = "This username is already taken. Please choose another one."
                elif "email" in error_msg:
                    user_message = "This email address is already registered. Please use a different one."
                else:
                    user_message = "This record already exists in our system."
            else:
                user_message = "A database constraint was violated. Please check your input."

        if settings.DEBUG:
            # In debug mode, re-raise the exception to see the traceback
            raise exception

        # Add the message to django messages framework
        messages.error(request, f"{user_message} (Error: {str(exception)})")

        # Check if we are on the login page to avoid infinite loop
        if request.path == reverse('login') or request.path.startswith('/accounts/login/'):
            # If the error happened ON the login page, rendering it again will likely cause the same error.
            # And redirecting to dashboard will redirect back to login (if not authenticated).
            # So we must NOT redirect. We should probably render a 500 error page or re-raise.
            raise exception

        # Attempt to redirect back to the referrer or a safe default
        referer = request.META.get('HTTP_REFERER')
        current_uri = request.build_absolute_uri()
        
        # AJAX/API Detection
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or \
                  'application/json' in request.headers.get('Accept', '') or \
                  '/api/' in request.path
        
        if is_ajax:
            return JsonResponse({
                'status': 'error',
                'message': user_message,
                'details': str(exception),
                'traceback': traceback.format_exc() if settings.DEBUG else None
            }, status=500)

        if referer and referer != current_uri:
            return redirect(referer)
        
        # Fallback to dashboard if no referer or if referer is the current page (to avoid loop)
        try:
             # Check if we are already on the dashboard to avoid infinite loop
            if resolve(request.path).url_name in ['dashboard', 'home']:
                from django.http import HttpResponseServerError
                return HttpResponseServerError(f"Critical Error on Dashboard: {user_message}")
        except:
            pass
            
        return redirect('dashboard')
