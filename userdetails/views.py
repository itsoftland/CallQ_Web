import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import User
from companydetails.models import Company, Branch
from callq_core.permissions import company_required
from callq_core.services import log_activity
from django.db.models import Q
from datetime import date

@login_required
@user_passes_test(company_required)
def user_list(request):
    user = request.user
    search_query = request.GET.get('search', '')
    if not search_query:
        search_query = request.GET.get('q', '') # Handle both legacy 'q' and new 'search' params
        
    role_filter = request.GET.get('role', '')
    branch_filter = request.GET.get('branch', '')

    # 1. Base User Query
    if user.role == "SUPER_ADMIN":
        users = User.objects.all()
    elif user.role == "ADMIN":
        if user.assigned_state:
            users = User.objects.filter(
                Q(company_relation__state__in=user.assigned_state) |
                Q(branch_relation__company__state__in=user.assigned_state) |
                Q(role='ADMIN', assigned_state__overlap=user.assigned_state)
            ).distinct()
        else:
            users = User.objects.none()
    elif user.role == "DEALER_ADMIN":
        if user.company_relation:
            # Dealer sees users of their company and their child companies
            users = User.objects.filter(
                Q(company_relation=user.company_relation) | 
                Q(company_relation__parent_company=user.company_relation) |
                Q(branch_relation__company=user.company_relation) |
                Q(branch_relation__company__parent_company=user.company_relation)
            )
        else:
            users = User.objects.none()
    elif user.role == "COMPANY_ADMIN":
        if user.company_relation:
             users = User.objects.filter(
                Q(company_relation=user.company_relation) |
                Q(branch_relation__company=user.company_relation)
            ).exclude(role='PRODUCTION_ADMIN')  # Company Admin cannot see Production Admins
        else:
            users = User.objects.none()
    elif user.role == "BRANCH_ADMIN":
         if user.branch_relation:
            users = User.objects.filter(branch_relation=user.branch_relation)
         else:
            users = User.objects.none()
    else:
        users = User.objects.none()
    
    # Exclude self from list (optional, but good for "manage users" context)
    # users = users.exclude(pk=user.pk) 

    # 2. Prepare Filters
    branches = Branch.objects.none()
    available_roles = []
    
    if user.role == "SUPER_ADMIN":
        branches = Branch.objects.all()
        available_roles = [
            ("SUPER_ADMIN", "Super Admin"), ("ADMIN", "Admin"), 
            ("DEALER_ADMIN", "Dealer Admin"), ("COMPANY_ADMIN", "Company Admin"), 
            ("BRANCH_ADMIN", "Branch Admin"), ("PRODUCTION_ADMIN", "Production Admin"), 
            ("EMPLOYEE", "Employee"), ("COMPANY_EMPLOYEE", "Company Employee")
        ]
    elif user.role == "ADMIN":
        if user.assigned_state:
             branches = Branch.objects.filter(company__state__in=user.assigned_state)
        available_roles = [
            ("DEALER_ADMIN", "Dealer Admin"), ("COMPANY_ADMIN", "Company Admin"), 
            ("BRANCH_ADMIN", "Branch Admin"), ("PRODUCTION_ADMIN", "Production Admin"), 
            ("EMPLOYEE", "Employee"), ("COMPANY_EMPLOYEE", "Company Employee")
        ]
    elif user.role == "DEALER_ADMIN":
        if user.company_relation:
            branches = Branch.objects.filter(
                Q(company=user.company_relation) |
                Q(company__parent_company=user.company_relation)
            )
        available_roles = [
            ("COMPANY_ADMIN", "Company Admin"), ("BRANCH_ADMIN", "Branch Admin"), 
            ("COMPANY_EMPLOYEE", "Company Employee")
        ]
    elif user.role == "COMPANY_ADMIN":
        if user.company_relation:
            branches = Branch.objects.filter(company=user.company_relation)
        available_roles = [
            ("BRANCH_ADMIN", "Branch Admin"), ("COMPANY_EMPLOYEE", "Company Employee")
        ]
    
    # 3. Apply Filters
    if search_query:
        users = users.filter(Q(email__icontains=search_query) | Q(username__icontains=search_query))
    if role_filter:
        users = users.filter(role=role_filter)
    if branch_filter and branches.filter(id=branch_filter).exists(): # Validate branch access
        users = users.filter(branch_relation_id=branch_filter)
        
    return render(request, 'userdetails/user_list.html', {
        'users': users,
        'search_query': search_query,
        'role_filter': role_filter,
        'branch_filter': branch_filter,
        'branches': branches,
        'available_roles': available_roles,
    })

def prepare_relations(request, selected_cid=None, selected_bid=None):
    user = request.user
    if user.role == 'SUPER_ADMIN':
        companies = Company.objects.all()
    elif user.role == 'ADMIN':
        companies = Company.objects.filter(state__in=user.assigned_state) if user.assigned_state else Company.objects.none()
    elif user.role == 'DEALER_ADMIN':
        if user.company_relation:
            # Dealer sees their DealerCustomer records in the dropdown
            from companydetails.models import DealerCustomer
            dealer_customers = list(DealerCustomer.objects.filter(dealer=user.company_relation))
            # Add attributes for template compatibility
            for dc in dealer_customers:
                dc.company_type = 'CUSTOMER'
                dc.is_dealer_customer = True  # Flag to identify in save logic
            
            # Fix: Add the dealer itself as the first option
            # This is crucial because the JS filters for 'DEALER' type for DEALER_ADMIN
            # and currently backend forces creation under the Dealer's company anyway.
            companies = [user.company_relation] + dealer_customers
        else:
            companies = []
    elif user.role == 'COMPANY_ADMIN':
        companies = [user.company_relation]
    elif user.role == 'EMPLOYEE':
        # Employee can only see companies in their assigned states
        if user.assigned_state:
            companies = Company.objects.filter(state__in=user.assigned_state)
        else:
            companies = Company.objects.none()
    else:
        companies = []

    for c in companies:
        c.is_selected = (str(c.id) == str(selected_cid))
    
    if user.role == 'SUPER_ADMIN':
        if selected_cid:
            branches = Branch.objects.filter(company_id=selected_cid)
        else:
            branches = Branch.objects.none()
    elif user.role in ['ADMIN', 'EMPLOYEE'] and user.assigned_state:
        if selected_cid:
            branches = Branch.objects.filter(company_id=selected_cid, company__state__in=user.assigned_state)
        else:
            branches = Branch.objects.none()
    elif user.role == 'DEALER_ADMIN':
        if user.company_relation:
            branches = Branch.objects.filter(
                Q(company=user.company_relation) |
                Q(company__parent_company=user.company_relation)
            )
        else:
            branches = Branch.objects.none()
    elif user.role == 'COMPANY_ADMIN':
        branches = Branch.objects.filter(company=user.company_relation)
    else:
        branches = Branch.objects.none()

    for b in branches:
        b.is_selected = (str(b.id) == str(selected_bid))

    # Detect single-branch scenario and auto-lock company for COMPANY_ADMIN / BRANCH_ADMIN
    single_branch = None
    auto_company = None
    if user.role in ['COMPANY_ADMIN', 'BRANCH_ADMIN']:
        auto_company = user.company_relation  # Always lock Company field for these roles
        branch_list = list(branches)
        if len(branch_list) == 1:
            single_branch = branch_list[0]

    return companies, branches, single_branch, auto_company

@login_required
@user_passes_test(company_required)
def user_create(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')
        company_id = request.POST.get('company')
        branch_id = request.POST.get('branch')
        assigned_states = request.POST.getlist('assigned_state')
        is_web_user = request.POST.get('is_web_user') == 'on'
        is_android_user = request.POST.get('is_android_user') == 'on'
        display_name = request.POST.get('display_name')
        username = email.split('@')[0] if email else None

        # Validation: Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, f"User with email {email} already exists.")
            companies, branches, single_branch, auto_company = prepare_relations(request, company_id, branch_id)
            return render(request, 'userdetails/user_form.html', {
                'companies': companies,
                'branches': branches,
                'single_branch': single_branch,
                'auto_company': auto_company,
                'title': 'Create User',
                'button_text': 'Create User',
                'roles': get_roles_for_user(request.user),
                'password_required': True,
                'form_data': request.POST,
                'edit_user': None
            })

        # Validation: Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, f"User with username '{username}' (generated from email) already exists.")
            companies, branches, single_branch, auto_company = prepare_relations(request, company_id, branch_id)
            return render(request, 'userdetails/user_form.html', {
                'companies': companies,
                'branches': branches,
                'single_branch': single_branch,
                'auto_company': auto_company,
                'title': 'Create User',
                'button_text': 'Create User',
                'roles': get_roles_for_user(request.user),
                'password_required': True,
                'form_data': request.POST,
                'edit_user': None
            })
        
        user = User.objects.create_user(username=username, email=email, password=password, role=role)
        user.display_name = display_name
        user.is_web_user = is_web_user
        user.is_android_user = is_android_user
        if role == 'ADMIN' and assigned_states:
            user.assigned_state = assigned_states
        elif role == 'EMPLOYEE' and assigned_states:
            user.assigned_state = assigned_states
        
        # Logic fix: Dealer Admins creates users linked to their company, even for EMPLOYEE/PRODUCTION roles
        if request.user.role == 'DEALER_ADMIN':
             # Check if selected company is a DealerCustomer
             from companydetails.models import DealerCustomer
             dc = DealerCustomer.objects.filter(id=company_id, dealer=request.user.company_relation).first()
             
             if dc:
                 user.dealer_customer_relation = dc
                 # Fix: Link to the Customer Company if it exists (company_id match)
                 customer_company = Company.objects.filter(company_id=dc.customer_id).first()
                 if customer_company:
                     user.company_relation = customer_company
                     user.role = 'COMPANY_ADMIN' # Role for customer admin
                 else:
                     # Fallback to Dealer if no company exists (Contact only)
                     user.company_relation = request.user.company_relation
                     user.role = 'COMPANY_ADMIN' # Keep consistent role
             else:
                 user.company_relation = request.user.company_relation
             
             if branch_id: user.branch_relation_id = branch_id 
        elif request.user.role == 'COMPANY_ADMIN':
            user.company_relation = request.user.company_relation
        elif role in ['SUPER_ADMIN', 'ADMIN', 'EMPLOYEE']:
            user.company_relation = None
            user.branch_relation = None
        elif role == 'PRODUCTION_ADMIN':
            # Production Admin can be linked to a company
            if company_id:
                user.company_relation_id = company_id
            else:
                user.company_relation = None
            user.branch_relation = None
        else:
            if company_id: user.company_relation_id = company_id
            if branch_id: user.branch_relation_id = branch_id
        
        user.save()
        log_activity(request.user, "User Created", f"Created user {user.email} with role {user.role}")
        messages.success(request, f"User {email} created successfully.")
        
        # Redirect dealers to My Users page, others to user_list
        if request.user.role == 'DEALER_ADMIN':
            return redirect('user_list') # Redirect to standard list filtered for dealers
        return redirect('user_list')
        
    companies, branches, single_branch, auto_company = prepare_relations(request)
    roles = get_roles_for_user(request.user)

    return render(request, 'userdetails/user_form.html', {
        'companies': companies, 
        'branches': branches,
        'single_branch': single_branch,
        'auto_company': auto_company,
        'title': 'Create User',
        'button_text': 'Create User',
        'roles': roles,
        'password_required': True,
        'edit_user': None,
        'form_data': {}
    })

def get_roles_for_user(user):
    """Helper to get allowed roles based on the current user's role."""
    if user.role == "SUPER_ADMIN":
        return [("SUPER_ADMIN", "Super Admin"), ("ADMIN", "Admin"), ("DEALER_ADMIN", "Dealer Admin"), ("COMPANY_ADMIN", "Company Admin"), ("BRANCH_ADMIN", "Branch Admin"), ("PRODUCTION_ADMIN", "Production Admin"), ("EMPLOYEE", "Employee"), ("COMPANY_EMPLOYEE", "Company Employee")]
    elif user.role == "ADMIN":
        return [("DEALER_ADMIN", "Dealer Admin"), ("COMPANY_ADMIN", "Company Admin"), ("BRANCH_ADMIN", "Branch Admin"), ("PRODUCTION_ADMIN", "Production Admin"), ("EMPLOYEE", "Employee"), ("COMPANY_EMPLOYEE", "Company Employee")]
    elif user.role == "DEALER_ADMIN":
        return [("COMPANY_ADMIN", "Company Admin"), ("BRANCH_ADMIN", "Branch Admin"), ("COMPANY_EMPLOYEE", "Company Employee")]
    elif user.role == "COMPANY_ADMIN":
        return [("BRANCH_ADMIN", "Branch Admin"), ("COMPANY_EMPLOYEE", "Company Employee")]
    return []

@login_required
@user_passes_test(company_required)
def user_edit(request, pk):
    user_to_edit = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        email = request.POST.get('email')
        role = request.POST.get('role')
        company_id = request.POST.get('company')
        branch_id = request.POST.get('branch')
        assigned_states = request.POST.getlist('assigned_state')
        password = request.POST.get('password')
        is_web_user = request.POST.get('is_web_user') == 'on'
        is_android_user = request.POST.get('is_android_user') == 'on'
        display_name = request.POST.get('display_name')
        username = email.split('@')[0] if email else None

        # Validation: Check if email already exists (excluding current user)
        if User.objects.filter(email=email).exclude(pk=pk).exists():
            messages.error(request, f"User with email {email} already exists.")
            companies, branches, single_branch, auto_company = prepare_relations(request, company_id, branch_id)
            return render(request, 'userdetails/user_form.html', {
                'edit_user': user_to_edit,
                'companies': companies,
                'branches': branches,
                'single_branch': single_branch,
                'auto_company': auto_company,
                'title': 'Update User',
                'button_text': 'Update User',
                'roles': get_roles_for_user(request.user),
                'password_required': False,
                'password_help': '(Optional)',
                'form_data': request.POST
            })

        # Validation: Check if username already exists (excluding current user)
        if User.objects.filter(username=username).exclude(pk=pk).exists():
            messages.error(request, f"User with username '{username}' (generated from email) already exists.")
            companies, branches, single_branch, auto_company = prepare_relations(request, company_id, branch_id)
            return render(request, 'userdetails/user_form.html', {
                'edit_user': user_to_edit,
                'companies': companies,
                'branches': branches,
                'single_branch': single_branch,
                'auto_company': auto_company,
                'title': 'Update User',
                'button_text': 'Update User',
                'roles': get_roles_for_user(request.user),
                'password_required': False,
                'password_help': '(Optional)',
                'form_data': request.POST
            })

        user_to_edit.email = email
        user_to_edit.username = username
        user_to_edit.role = role
        user_to_edit.is_web_user = is_web_user
        user_to_edit.is_android_user = is_android_user
        user_to_edit.display_name = display_name
        if password: user_to_edit.set_password(password)

        if role in ['ADMIN', 'SUPER_ADMIN', 'EMPLOYEE']:
            user_to_edit.assigned_state = assigned_states if role in ['ADMIN', 'EMPLOYEE'] else []
            user_to_edit.company_relation = None
            user_to_edit.branch_relation = None
            user_to_edit.dealer_customer_relation = None # Clear if switched to system role
        elif role == 'PRODUCTION_ADMIN':
            user_to_edit.assigned_state = []
            # Production Admin can be linked to a company
            if company_id:
                user_to_edit.company_relation_id = company_id
            else:
                user_to_edit.company_relation = None
            user_to_edit.branch_relation = None
            user_to_edit.dealer_customer_relation = None
        else:
            user_to_edit.assigned_state = []
            if request.user.role == 'DEALER_ADMIN':
                from companydetails.models import DealerCustomer
                dc = DealerCustomer.objects.filter(id=company_id, dealer=request.user.company_relation).first()
                if dc:
                    user_to_edit.dealer_customer_relation = dc
                    # Fix: Link to the Customer Company if it exists
                    customer_company = Company.objects.filter(company_id=dc.customer_id).first()
                    if customer_company:
                        user_to_edit.company_relation = customer_company
                    else:
                        user_to_edit.company_relation = request.user.company_relation
                    user_to_edit.role = 'COMPANY_ADMIN'
                else:
                    user_to_edit.dealer_customer_relation = None
                    user_to_edit.company_relation = request.user.company_relation
            else:
                user_to_edit.company_relation_id = company_id
                user_to_edit.dealer_customer_relation = None
                
            user_to_edit.branch_relation_id = branch_id
        
        user_to_edit.save()
        log_activity(request.user, "User Updated", f"Updated user {user_to_edit.email}")
        messages.success(request, f"User {user_to_edit.email} updated successfully.")
        return redirect('user_list')

    companies, branches, single_branch, auto_company = prepare_relations(request, user_to_edit.company_relation_id, user_to_edit.branch_relation_id)
    roles = get_roles_for_user(request.user)

    for r_val, r_name in roles:
        if r_val == user_to_edit.role:
            user_to_edit.role_name = r_name # for template simplicity if needed

    return render(request, 'userdetails/user_form.html', {
        'edit_user': user_to_edit,
        'companies': companies,
        'branches': branches,
        'single_branch': single_branch,
        'auto_company': auto_company,
        'title': 'Update User',
        'button_text': 'Update User',
        'roles': roles,
        'password_required': False,
        'password_help': '(Optional)',
        'form_data': {}
    })

@login_required
@user_passes_test(company_required)
def user_delete(request, pk):
    user_to_delete = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        email = user_to_delete.email
        user_to_delete.delete()
        log_activity(request.user, "User Deleted", f"Deleted user {email}")
        messages.success(request, f"User {email} deleted successfully.")
        return redirect('user_list')
    return redirect('user_list')

@login_required
@user_passes_test(company_required)
def user_toggle_status(request, pk):
    user_to_toggle = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user_to_toggle.is_active = not user_to_toggle.is_active
        user_to_toggle.save()
        status = "Activated" if user_to_toggle.is_active else "Deactivated"
        log_activity(request.user, "User Status Toggled", f"{status} user {user_to_toggle.email}")
        messages.success(request, f"User {user_to_toggle.email} {status.lower()} successfully.")
    return redirect('user_list')

# --- API ---
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response as DRFResponse
from configdetails.models import Device

# --- Serialization Helpers for Android APIs ---

def serialize_company_full(company):
    if not company: return None
    return {
        "id": company.id,
        "company_id": company.company_id,
        "name": company.company_name,
        "type": company.company_type,
        "email": company.company_email,
        "gst": company.gst_number,
        "contact_person": company.contact_person,
        "contact_number": company.contact_number,
        "address": company.address,
        "address_2": company.address_2,
        "city": company.city,
        "district": company.district,
        "state": company.state,
        "zip_code": company.zip_code
    }

def serialize_dealer_customer_full(dc):
    if not dc: return None
    return {
        "id": dc.id,
        "customer_id": dc.customer_id,
        "name": dc.company_name,
        "email": dc.company_email,
        "gst": dc.gst_number,
        "contact_person": dc.contact_person,
        "contact_number": dc.contact_number,
        "address": dc.address,
        "address_2": dc.address_2,
        "city": dc.city,
        "district": dc.district,
        "state": dc.state,
        "zip_code": dc.zip_code,
        "dealer_id": dc.dealer.id,
        "dealer_name": dc.dealer.company_name
    }

def serialize_branch_full(branch):
    if not branch: return None
    return {
        "id": branch.id,
        "name": branch.branch_name,
        "address": branch.address,
        "city": branch.city,
        "state": branch.state,
        "zip_code": branch.zip_code
    }

def serialize_device_full(device):
    if not device: return None
    from configdetails.models import Mapping
    
    # Base device info
    data = {
        "id": device.id,
        "serial_number": device.serial_number,
        "mac_address": device.mac_address,
        "device_type": device.device_type,
        "device_model": device.device_model,
        "licence_status": device.licence_status,
        "licence_active_to": str(device.licence_active_to) if device.licence_active_to else None,
        "is_active": device.is_active,
        "branch": serialize_branch_full(device.branch) if device.branch else None,
        "config": {}
    }
    
    # Configuration
    if hasattr(device, 'config'):
        data["config"]["general"] = device.config.config_json
    
    if device.device_type == 'TV' and hasattr(device, 'tv_config'):
        tc = device.tv_config
        data["config"]["tv"] = {
            "orientation": tc.orientation,
            "layout_type": tc.layout_type,
            "display_rows": tc.display_rows,
            "display_columns": tc.display_columns,
            "token_audio_file": tc.token_audio_file.url if tc.token_audio_file else None,
            "audio_language": tc.audio_language,
            "token_format": tc.token_format,
            "no_of_counters": tc.no_of_counters,
            "ad_placement": getattr(tc, 'ad_placement', 'right'),
            "ads": [ad.file.url for ad in tc.ads.all()]
        }
        
    if device.device_type == 'LED' and hasattr(device, 'led_config'):
        lc = device.led_config
        data["config"]["led"] = {
            "identifier": lc.led_identifier_name,
            "voice_announcement": lc.voice_announcement,
            "counter_number": lc.counter_number,
            "token_calling": lc.token_calling
        }
        
    if device.embedded_profile:
        data["config"]["embedded"] = device.embedded_profile.config_json

    # Mappings
    mappings = Mapping.objects.filter(Q(tv=device) | Q(token_dispenser=device) | Q(keypad=device) | Q(broker=device) | Q(led=device))
    data["mappings"] = []
    for m in mappings:
        m_data = {
            "id": m.id,
            "tv": m.tv.serial_number if m.tv else None,
            "token_dispenser": m.token_dispenser.serial_number if m.token_dispenser else None,
            "keypad": m.keypad.serial_number if m.keypad else None,
            "broker": m.broker.serial_number if m.broker else None,
            "led": m.led.serial_number if m.led else None
        }
        data["mappings"].append(m_data)

    return data

def serialize_device_minimal(device):
    """
    Returns base device information and mappings only, excluding config and profiles.
    """
    if not device: return None
    from configdetails.models import Mapping
    
    # Base device info
    data = {
        "id": device.id,
        "serial_number": device.serial_number,
        "mac_address": device.mac_address,
        "device_type": device.device_type,
        "device_model": device.device_model,
        "licence_status": device.licence_status,
        "licence_active_to": str(device.licence_active_to) if device.licence_active_to else None,
        "is_active": device.is_active,
        "branch": serialize_branch_full(device.branch) if device.branch else None,
    }
    
    # Mappings (Legacy)
    mappings = Mapping.objects.filter(Q(tv=device) | Q(token_dispenser=device) | Q(keypad=device) | Q(broker=device) | Q(led=device))
    data["mappings"] = []
    for m in mappings:
        m_data = {
            "id": m.id,
            "tv": m.tv.serial_number if m.tv else None,
            "token_dispenser": m.token_dispenser.serial_number if m.token_dispenser else None,
            "keypad": m.keypad.serial_number if m.keypad else None,
            "broker": m.broker.serial_number if m.broker else None,
            "led": m.led.serial_number if m.led else None
        }
        data["mappings"].append(m_data)

    return data

@api_view(['POST'])
@permission_classes([AllowAny])
def android_employee_login_api(request):
    """
    Specialized login API for Android Employee devices.

    Accepts an optional 'app_type' field in the request body:
      - 'config'           : Android Config app (default behaviour, no extra restriction)
      - 'serial_numbering' : Serial Numbering app — only PRODUCTION_ADMIN role is allowed
    """
    from companydetails.models import DealerCustomer
    from configdetails.views import get_used_locations, get_flattened_used_locations
    
    username = request.data.get('username')
    password = request.data.get('password')
    mac_address = request.data.get('mac_address')
    customer_id = request.data.get('customer_id') # maps to Company.company_id or DealerCustomer.customer_id

    # app_type flag: 'config' (default) | 'serial_numbering'
    app_type = request.data.get('app_type', 'config').strip().lower()
    VALID_APP_TYPES = ('config', 'serial_numbering')
    if app_type not in VALID_APP_TYPES:
        return DRFResponse({
            "error": "Invalid app_type",
            "message": f"app_type must be one of: {', '.join(VALID_APP_TYPES)}."
        }, status=status.HTTP_400_BAD_REQUEST)

    # Validate required fields
    if not all([username, password, mac_address]):
        return DRFResponse({"error": "Invalid request data."}, status=status.HTTP_400_BAD_REQUEST)

    # Authenticate user credentials first
    user = authenticate(username=username, password=password)
    
    if not user:
        return DRFResponse({
            "error": "Invalid user id or password",
            "message": "The username or password provided is incorrect."
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    if not user.is_android_user:
        return DRFResponse({
            "error": "Android access denied",
            "message": "This account does not have Android application access."
        }, status=status.HTTP_403_FORBIDDEN)

    # --- app_type access control ---
    # Serial numbering app is restricted to PRODUCTION_ADMIN role only
    if app_type == 'serial_numbering' and user.role != 'PRODUCTION_ADMIN':
        return DRFResponse({
            "error": "Access denied",
            "message": "The Serial Numbering app is only accessible to Production Admin accounts."
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Find the company/dealer_customer from customer_id
    company = None
    dealer_customer = None
    is_dealer_customer = False
    
    if customer_id:
        # Check if customer_id starts with 0 and slice it
        if str(customer_id).startswith('0'):
            customer_id = str(customer_id)[1:]
        
        # Try matching Company by ID (if int) or company_id string
        if str(customer_id).isdigit():
            company = Company.objects.filter(id=customer_id).first()
        
        if not company:
            company = Company.objects.filter(company_id=customer_id).first()
        
        # If no Company found, try DealerCustomer
        if not company:
            dealer_customer = DealerCustomer.objects.filter(customer_id=customer_id).first()
            if dealer_customer:
                is_dealer_customer = True
                company = dealer_customer.dealer
        
        if not company:
            return DRFResponse({
                "error": "Invalid customer id",
                "message": "The customer id provided is not valid."
            }, status=status.HTTP_404_NOT_FOUND)
    else:
        # customer_id missing - only allowed for System Admins
        if user.role not in ["SUPER_ADMIN", "ADMIN"]:
             return DRFResponse({
                "error": "Invalid request data",
                "message": "customer_id is required."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Find the device early for System Admins without customer_id
        device = Device.objects.filter(
            Q(mac_address=mac_address) | Q(serial_number=mac_address)
        ).first()

        if not device:
            return DRFResponse({
                "error": "Device not found",
                "message": "customer_id is required for un-registered devices."
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Pull company/customer context from device registration
        if device.dealer_customer:
            dealer_customer = device.dealer_customer
            company = dealer_customer.dealer
            is_dealer_customer = True
        else:
            company = device.company

    # Check if user's company matches the customer_id (skip for System Admins)
    if user.role not in ["SUPER_ADMIN", "ADMIN"]:
        is_direct_match = (user.company_relation and user.company_relation == company)
        is_dealer_match = (user.role == "DEALER_ADMIN" and company.parent_company == user.company_relation)
        
        if not (is_direct_match or is_dealer_match):
            return DRFResponse({
                "error": "Invalid user id or password",
                "message": "The user is not associated with this customer."
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Find the device by mac_address
    device = Device.objects.filter(
        Q(mac_address=mac_address) | Q(serial_number=mac_address)
    ).first()
    
    if not device:
        return DRFResponse({
            "error": "Device not found",
            "message": "The device with the provided MAC address is not registered. Please contact admin."
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check if device is mapped to the customer
    device_matches_customer = False
    
    if is_dealer_customer:
        # For dealer customer, check if device is assigned to this dealer_customer
        # OR if device belongs to the dealer company (parent)
        device_matches_customer = (
            device.dealer_customer == dealer_customer or 
            (device.company == company and device.dealer_customer is None)
        )
    else:
        # For regular company, check if device belongs to this company
        device_matches_customer = (device.company == company)
    
    if not device_matches_customer:
        return DRFResponse({
            "error": "Device is mapped to another customer",
            "message": "The device with the provided MAC address is registered under a different customer."
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Check device status
    if device.licence_status != 'Active':
        return DRFResponse({
            "status": "pending",
            "response": "Waiting for Approval | Contact Admin"
        })
    
    # Store Login History
    from .models import AppLoginHistory
    login_version = request.data.get('version')
    AppLoginHistory.objects.create(
        user=user,
        company=company,
        mac_address=mac_address,
        version=login_version
    )
    
    # Route specific to the logged-in user's company
    route_c_ids = [user.company_relation.id] if user.company_relation else []
    route_dc_ids = []
    if user.role == "DEALER_CUSTOMER":
        user_dc = DealerCustomer.objects.filter(company_email=user.email).first()
        if not user_dc and user.company_relation:
            user_dc = DealerCustomer.objects.filter(dealer=user.company_relation).first()
        if user_dc:
            route_dc_ids.append(user_dc.id)

    # For Super Admin logging in without a specific customer_id, return everything
    if user.role == "SUPER_ADMIN" and not request.data.get('customer_id'):
        companies = Company.objects.all()
        customers_data = []
        for c in companies:
            c_data = serialize_company_full(c)
            c_data["devices"] = [serialize_device_full(d) for d in Device.objects.filter(company=c)]
            customers_data.append(c_data)
            
        dealer_customers = DealerCustomer.objects.all()
        for dc in dealer_customers:
            dc_data = serialize_dealer_customer_full(dc)
            dc_data["devices"] = [serialize_device_full(d) for d in Device.objects.filter(dealer_customer=dc)]
            customers_data.append(dc_data)

        return DRFResponse({
            "status": "success",
            "response": "Login Approved",
            "app_type": app_type,
            "Route": get_flattened_used_locations(company_ids=route_c_ids, dealer_customer_ids=route_dc_ids),
            "user_info": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            },
            "customers": customers_data,
            "device": serialize_device_full(device)
        })

    return DRFResponse({
        "status": "success",
        "response": "Login Approved",
        "app_type": app_type,
        "Route": get_flattened_used_locations(company_ids=route_c_ids, dealer_customer_ids=route_dc_ids),
        "user_info": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        },
        "customer": serialize_dealer_customer_full(dealer_customer) if is_dealer_customer else serialize_company_full(company),
        "device": serialize_device_full(device)
    })

@login_required
@user_passes_test(company_required)
def app_login_history(request):
    """View to list Android app login history, filtered by user's company."""
    from .models import AppLoginHistory
    user = request.user
    
    if user.role in ["SUPER_ADMIN", "ADMIN"]:
        history = AppLoginHistory.objects.all()
    elif user.role == "DEALER_ADMIN":
        if user.company_relation:
            history = AppLoginHistory.objects.filter(
                Q(company=user.company_relation) | 
                Q(company__parent_company=user.company_relation)
            )
        else:
            history = AppLoginHistory.objects.none()
    elif user.role == "COMPANY_ADMIN":
        history = AppLoginHistory.objects.filter(company=user.company_relation)
    else:
        history = AppLoginHistory.objects.none()

    # Search functionality
    q = request.GET.get('q', '')
    if q:
        history = history.filter(
            Q(user__username__icontains=q) | 
            Q(user__email__icontains=q) | 
            Q(mac_address__icontains=q) |
            Q(version__icontains=q)
        )

    return render(request, 'userdetails/app_login_history.html', {
        'history': history,
        'q': q
    })

@login_required
def profile(request):
    from companydetails.models import DealerCustomer
    user = request.user
    company = user.company_relation
    dealer_customer = user.dealer_customer_relation
    
    # For dealer-created company admins, dealer_customer_relation should always be set
    # If it's not set but user is COMPANY_ADMIN with dealer-created company, show warning
    if user.role == "COMPANY_ADMIN" and company and company.is_dealer_created and not dealer_customer:
        messages.warning(request, "Your account is missing dealer customer information. Please contact your dealer administrator.")
    
    if request.method == 'POST':
        email = request.POST.get('email')
        
        # User details update
        if email:
            if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                messages.error(request, "This email is already in use by another account.")
            else:
                user.email = email
                user.username = email.split('@')[0]
                user.save()
                
                # Company details update (only for COMPANY_ADMIN or DEALER_ADMIN)
                # For dealer-created company admins (user.dealer_customer_relation is set), update DealerCustomer instead
                if user.dealer_customer_relation:
                    # Dealer-created company admin: update DealerCustomer details
                    dealer_customer = user.dealer_customer_relation
                    dealer_customer.company_name = request.POST.get('company_name', dealer_customer.company_name)
                    dealer_customer.gst_number = request.POST.get('gst_number', dealer_customer.gst_number)
                    dealer_customer.contact_person = request.POST.get('contact_person', dealer_customer.contact_person)
                    dealer_customer.contact_number = request.POST.get('contact_number', dealer_customer.contact_number)
                    dealer_customer.address = request.POST.get('address', dealer_customer.address)
                    dealer_customer.city = request.POST.get('city', dealer_customer.city)
                    dealer_customer.district = request.POST.get('district', dealer_customer.district)
                    dealer_customer.state = request.POST.get('state', dealer_customer.state)
                    dealer_customer.zip_code = request.POST.get('zip_code', dealer_customer.zip_code)
                    dealer_customer.save()
                elif company and user.role in ['COMPANY_ADMIN', 'DEALER_ADMIN']:
                    # Normal company admin: update Company details
                    company.company_name = request.POST.get('company_name', company.company_name)
                    company.gst_number = request.POST.get('gst_number', company.gst_number)
                    company.contact_person = request.POST.get('contact_person', company.contact_person)
                    company.contact_number = request.POST.get('contact_number', company.contact_number)
                    company.address = request.POST.get('address', company.address)
                    company.city = request.POST.get('city', company.city)
                    company.district = request.POST.get('district', company.district)
                    company.state = request.POST.get('state', company.state)
                    company.zip_code = request.POST.get('zip_code', company.zip_code)
                    company.save()
                
                log_activity(user, "Profile Updated", f"User {user.email} updated their profile/company details.")
                messages.success(request, "Your profile and company details have been updated successfully.")
                return redirect('profile')
        else:
            messages.error(request, "Email is required.")

    return render(request, 'userdetails/profile.html', {
        'user': user,
        'company': company,
        'dealer_customer': dealer_customer
    })

@login_required
def trigger_password_reset(request):
    """
    Directly initiates a password reset for the logged-in user and returns JSON.
    """
    from django.contrib.auth.forms import PasswordResetForm
    from django.http import JsonResponse
    
    form = PasswordResetForm({'email': request.user.email})
    if form.is_valid():
        form.save(
            request=request,
            use_https=request.is_secure(),
            email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
        )
        log_activity(request.user, "Password Reset Triggered", f"User {request.user.email} triggered a password reset link.")
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': 'Password reset link has been sent to your email.'})
            
        messages.success(request, "Password reset link has been sent to your email.")
        return redirect('password_reset_done')
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Could not initiate password reset.'}, status=400)
            
        messages.error(request, "Could not initiate password reset. Please contact support.")
        return redirect('profile')


@api_view(['POST'])
@permission_classes([AllowAny])
def android_config_login(request):
    """
    Android login API for Config and Serial Numbering apps.

    Accepts an optional 'app_type' field in the request body:
      - 'config'           : Android Config app (default, no extra restriction)
      - 'serial_numbering' : Serial Numbering app — only PRODUCTION_ADMIN role is allowed
    """
    from companydetails.models import DealerCustomer
    from configdetails.views import get_used_locations, get_flattened_used_locations
    from configdetails.models import Device

    username = request.data.get('username')
    password = request.data.get('password')
    mac_address = request.data.get('mac_address')

    # app_type flag: 'config' (default) | 'serial_numbering'
    app_type = (request.data.get('app_type') or 'config').strip().lower()
    VALID_APP_TYPES = ('config', 'serial_numbering')
    if app_type not in VALID_APP_TYPES:
        return DRFResponse({
            "status": "error",
            "error": "Invalid app_type",
            "message": f"app_type must be one of: {', '.join(VALID_APP_TYPES)}."
        }, status=status.HTTP_400_BAD_REQUEST)

    if not all([username, password, mac_address]):
        return DRFResponse({
            "status": "error",
            "error": "Invalid request data",
            "message": "Username, password, and mac_address are required."
        }, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(username=username, password=password)
    
    if not user:
        return DRFResponse({
            "status": "error",
            "error": "Invalid credentials",
            "message": "The username or password provided is incorrect."
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    if not user.is_active:
        return DRFResponse({
            "status": "error",
            "error": "Account disabled",
            "message": "This account has been deactivated."
        }, status=status.HTTP_401_UNAUTHORIZED)

    if not user.is_android_user:
        return DRFResponse({
            "status": "error",
            "error": "Android access denied",
            "message": "This account does not have Android application access."
        }, status=status.HTTP_403_FORBIDDEN)

    # --- app_type access control ---
    # Serial Numbering app is restricted to PRODUCTION_ADMIN role only
    if app_type == 'serial_numbering' and user.role != 'PRODUCTION_ADMIN':
        return DRFResponse({
            "status": "error",
            "error": "Access denied",
            "message": "The Serial Numbering app is only accessible to Production Admin accounts."
        }, status=status.HTTP_403_FORBIDDEN)

    # --- Device Approval Check ---
    device = Device.objects.filter(Q(mac_address=mac_address) | Q(serial_number=mac_address)).first()
    
    if not device:
        # Auto-create pending device request
        if user.company_relation:
            # If user is a dealer customer, attempt to link it to their specific record
            dealer_cust = None
            if user.role == "DEALER_CUSTOMER":
                dealer_cust = DealerCustomer.objects.filter(company_email=user.email).first()
            
            device = Device.objects.create(
                serial_number=mac_address,
                mac_address=mac_address,
                company=user.company_relation,
                dealer_customer=dealer_cust,
                licence_status='Pending',
                is_active=False,
                device_type='TV', 
                device_model='Android'
            )
        elif user.role in ["SUPER_ADMIN", "ADMIN"]:
            # Super Admin/Admin can register devices without an initial company
            device = Device.objects.create(
                serial_number=mac_address,
                mac_address=mac_address,
                company=None,
                dealer_customer=None,
                licence_status='Pending',
                is_active=False,
                device_type='TV', 
                device_model='Android'
            )
        else:
             return DRFResponse({
                "status": "error",
                "error": "No company assigned",
                "message": "User must be associated with a company to register devices."
            }, status=status.HTTP_403_FORBIDDEN)

    # Validate mapping for existing devices (skip for System Admins)
    if user.role not in ["SUPER_ADMIN", "ADMIN"]:
        is_owner = (device.company == user.company_relation)
        is_sub_customer = (device.dealer_customer and device.dealer_customer.dealer == user.company_relation)
        
        if not (is_owner or is_sub_customer):
             return DRFResponse({
                "status": "error",
                "error": "Device mapped to another customer",
                "message": "The device with the provided MAC address is registered under a different company."
            }, status=status.HTTP_403_FORBIDDEN)

    if device.licence_status != 'Active':
        return DRFResponse({
            "status": "pending",
            "response": "Waiting for Approval | Contact Admin",
            "message": f"Device with MAC {mac_address} is waiting for administrator approval."
        })
    # -----------------------------
    # Store Login History
    from .models import AppLoginHistory
    login_version = request.data.get('version')
    
    # Determine company for history (mandatory field in model)
    history_company = user.company_relation
    if not history_company and device:
        history_company = device.company
        
    if history_company:
        AppLoginHistory.objects.create(
            user=user,
            company=history_company,
            mac_address=mac_address,
            version=login_version
        )
    # -----------------------------

    user_info = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "display_name": user.display_name
    }

    # Restrict Route to only the logged in user's company locations
    route_c_ids = [user.company_relation.id] if user.company_relation else []
    route_dc_ids = []
    if user.role == "DEALER_CUSTOMER":
        user_dc = DealerCustomer.objects.filter(company_email=user.email).first()
        if not user_dc and user.company_relation:
            user_dc = DealerCustomer.objects.filter(dealer=user.company_relation).first()
        if user_dc:
            route_dc_ids.append(user_dc.id)

    customers_data = []
    company_ids = []
    dealer_customer_ids = []

    # Build customer list based on role and collect IDs for location filtering
    if user.role == "SUPER_ADMIN":
        # Super Admin sees ALL companies and ALL locations
        for company in Company.objects.all():
            customers_data.append(serialize_company_full(company))
            company_ids.append(company.id)
        # dealer_customer_ids remains empty for Super Admins
    
    elif user.role == "ADMIN":
        # Admin sees only companies in their assigned state(s)
        admin_states = user.assigned_state or []
        if admin_states:
            companies_qs = Company.objects.filter(state__in=admin_states)
        else:
            # If no assigned states, show no companies
            companies_qs = Company.objects.none()
        
        for company in companies_qs:
            customers_data.append(serialize_company_full(company))
            company_ids.append(company.id)

    elif user.role == "COMPANY_ADMIN":
        if user.company_relation:
            customers_data.append(serialize_company_full(user.company_relation))
            company_ids.append(user.company_relation.id)

    elif user.role == "DEALER_ADMIN":
        if user.company_relation:
            # Dealer's own company
            customers_data.append(serialize_company_full(user.company_relation))
            company_ids.append(user.company_relation.id)
            
            # Dealer's child companies (Dealer-created Companies)
            for child in Company.objects.filter(parent_company=user.company_relation):
                customers_data.append(serialize_company_full(child))
                company_ids.append(child.id)

            # Dealer's customers (DealerCustomer records)
            for dc in DealerCustomer.objects.filter(dealer=user.company_relation):
                customers_data.append(serialize_dealer_customer_full(dc))
                dealer_customer_ids.append(dc.id)

    elif user.role == "DEALER_CUSTOMER":
        # Specific dealer customer
        dealer_customer = DealerCustomer.objects.filter(company_email=user.email).first()
        if not dealer_customer and user.company_relation:
             dealer_customer = DealerCustomer.objects.filter(dealer=user.company_relation).first()
        
        if dealer_customer:
            customers_data.append(serialize_dealer_customer_full(dealer_customer))
            dealer_customer_ids.append(dealer_customer.id)

    # Determine states filter for Route (only for ADMIN role)
    route_states = None
    if user.role == "ADMIN" and user.assigned_state:
        route_states = user.assigned_state

    return DRFResponse({
        "status": "success",
        "response": "Login Approved",
        "Route": get_flattened_used_locations(company_ids=route_c_ids, dealer_customer_ids=route_dc_ids, states=route_states),
        "user_info": user_info,
        "customers": customers_data
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def getDeviceByCustomer(request):
    """
    Step 2 of the two-step login process for Android.
    Input: customer_id, name.
    Returns: Device list with configurations including TVs with mappings and TV configs.
    """
    from companydetails.models import DealerCustomer
    from configdetails.models import Device, Mapping, TVCounter, GroupMapping

    customer_id = request.data.get('customer_id')
    customer_name = request.data.get('name')

    if not customer_id:
        return DRFResponse({
            "status": "error",
            "error": "Invalid request data",
            "message": "customer_id is required."
        }, status=status.HTTP_400_BAD_REQUEST)

    # Clean customer_id (remove leading zero if present)
    clean_id = str(customer_id)
    if clean_id.startswith('0'):
        clean_id = clean_id[1:]

    # Find the target entity
    company = None
    dealer_customer = None
    
    # Check Company
    if clean_id.isdigit():
        company = Company.objects.filter(id=clean_id).first()
    if not company:
        company = Company.objects.filter(company_id=clean_id).first()
    
    # Check DealerCustomer
    if not company:
        if clean_id.isdigit():
            dealer_customer = DealerCustomer.objects.filter(id=clean_id).first()
        if not dealer_customer:
            dealer_customer = DealerCustomer.objects.filter(customer_id=clean_id).first()

    if not company and not dealer_customer:
        return DRFResponse({
            "status": "error",
            "error": "Customer not found",
            "message": f"Could not find a customer with ID '{customer_id}'."
        }, status=status.HTTP_404_NOT_FOUND)

    # Fetch all devices for this customer
    if dealer_customer:
        all_devices = Device.objects.filter(dealer_customer=dealer_customer)
    else:
        all_devices = Device.objects.filter(company=company, dealer_customer__isnull=True)

    # Separate devices: non-TV devices and TV devices
    non_tv_devices = all_devices.exclude(device_type='TV')
    tv_devices = all_devices.filter(device_type='TV')

    # Helper function to serialize group information
    def serialize_group(group):
        """Serialize a GroupMapping object with all its devices"""
        return {
            'id': group.id,
            'group_name': group.group_name,
            'dispensers': [{
                'id': d.id,
                'serial_number': d.serial_number,
                'display_name': d.display_name,
                'device_type': d.device_type,
                'token_type': d.token_type if d.device_type == Device.DeviceType.TOKEN_DISPENSER else None
            } for d in group.dispensers.all()],
            'keypads': [{
                'id': d.id,
                'serial_number': d.serial_number,
                'display_name': d.display_name,
                'device_type': d.device_type
            } for d in group.keypads.all()],
            'leds': [{
                'id': d.id,
                'serial_number': d.serial_number,
                'display_name': d.display_name,
                'device_type': d.device_type
            } for d in group.leds.all()],
            'brokers': [{
                'id': d.id,
                'serial_number': d.serial_number,
                'display_name': d.display_name,
                'device_type': d.device_type
            } for d in group.brokers.all()],
            'tvs': [{
                'id': d.id,
                'serial_number': d.serial_number,
                'display_name': d.display_name,
                'device_type': d.device_type
            } for d in group.tvs.all()]
        }

    # Helper function to find groups for a device
    def get_device_groups(device):
        """Get all GroupMapping objects that contain this device"""
        groups = []
        
        # Check each device type's reverse relation
        if device.device_type == Device.DeviceType.TOKEN_DISPENSER:
            groups = list(device.group_dispensers.all())
        elif device.device_type == Device.DeviceType.KEYPAD:
            groups = list(device.group_keypads.all())
        elif device.device_type == Device.DeviceType.LED:
            groups = list(device.group_leds.all())
        elif device.device_type == Device.DeviceType.BROKER:
            groups = list(device.group_brokers.all())
        elif device.device_type == Device.DeviceType.TV:
            groups = list(device.group_tvs.all())
        
        return groups

    # Helper function to serialize device with group information
    def serialize_device_with_group(device):
        device_data = serialize_device_minimal(device)
        
        # Get groups for this device
        groups = get_device_groups(device)
        
        # For Token Dispenser, Keypad, and LED: only one group allowed
        # For Broker and TV: can be in multiple groups
        if groups:
            if len(groups) == 1:
                # Single group - return the group object
                device_data['group'] = serialize_group(groups[0])
            else:
                # Multiple groups (only for Broker and TV)
                device_data['groups'] = [serialize_group(g) for g in groups]
        else:
            device_data['group'] = None
        
        return device_data

    # Helper function to serialize TV device with group information
    def serialize_tv_full(tv_device):
        tv_data = serialize_device_minimal(tv_device)
        
        # Get groups for this TV (TVs can be in multiple groups)
        groups = get_device_groups(tv_device)
        
        if groups:
            if len(groups) == 1:
                tv_data['group'] = serialize_group(groups[0])
            else:
                tv_data['groups'] = [serialize_group(g) for g in groups]
        else:
            tv_data['group'] = None
        
        return tv_data

    return DRFResponse({
        "status": "success",
        "customer_id": customer_id,
        "customer_name": customer_name,
        "devices": [serialize_device_with_group(d) for d in non_tv_devices],
        "tvs": [serialize_tv_full(tv) for tv in tv_devices]
    })

# Force reload
