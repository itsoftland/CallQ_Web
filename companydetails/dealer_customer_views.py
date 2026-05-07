from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import DealerCustomer, Company
from callq_core.permissions import dealer_required
from callq_core.services import log_activity
from django.db.models import Q
from django.core.paginator import Paginator
from userdetails.models import User as UserAccount
from configdetails.models import Mapping, ButtonMapping


@login_required
@user_passes_test(dealer_required)
def dealer_customer_list(request):
    """
    List all customers created by the logged-in dealer with pagination and filtering.
    """
    user = request.user
    
    if user.role != 'DEALER_ADMIN' or not user.company_relation:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    dealer = user.company_relation
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    # Get all dealer customers for this dealer
    customers = DealerCustomer.objects.filter(dealer=dealer)
    
    # Apply search filter
    if search_query:
        customers = customers.filter(
            Q(company_name__icontains=search_query) |
            Q(company_email__icontains=search_query) |
            Q(customer_id__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(contact_number__icontains=search_query)
        )
    
    # Apply status filter
    if status_filter:
        if status_filter == 'active':
            customers = customers.filter(is_active=True)
        elif status_filter == 'inactive':
            customers = customers.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(customers, 20)  # 20 customers per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'companydetails/dealer_customer_list.html', {
        'page_obj': page_obj,
        'customers': page_obj,  # For backward compatibility
        'search_query': search_query,
        'status_filter': status_filter
    })


@login_required
@user_passes_test(dealer_required)
def dealer_customer_create(request):
    """
    Create a new dealer customer contact record (no login account).
    """
    user = request.user
    
    if user.role != 'DEALER_ADMIN' or not user.company_relation:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    dealer = user.company_relation
    
    if request.method == 'POST':
        # Get form data
        company_name = request.POST.get('company_name')
        company_email = request.POST.get('company_email')
        contact_person = request.POST.get('contact_person')
        contact_number = request.POST.get('contact_number')
        address = request.POST.get('address')
        address_2 = request.POST.get('address_2', '')
        city = request.POST.get('city')
        district = request.POST.get('district', '')
        state = request.POST.get('state')
        zip_code = request.POST.get('zip_code')
        gst_number = request.POST.get('gst_number', '')
        
        # Validate required fields
        if not all([company_name, company_email, contact_person, contact_number, address, city, state, zip_code]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'companydetails/dealer_customer_form.html', {
                'title': 'Create Customer Contact',
                'button_text': 'Create Customer'
            })
        
        # Check if email already exists
        if DealerCustomer.objects.filter(company_email=company_email).exists():
            messages.error(request, "Email already exists.")
            return render(request, 'companydetails/dealer_customer_form.html', {
                'title': 'Create Customer Contact',
                'button_text': 'Create Customer'
            })
        
        # Generate customer ID
        customer_count = DealerCustomer.objects.filter(dealer=dealer).count()
        customer_id = f"{dealer.company_id or dealer.id} - {str(customer_count + 1).zfill(4)}"
        
        # Create dealer customer (contact record only)
        dealer_customer = DealerCustomer.objects.create(
            dealer=dealer,
            customer_id=customer_id,
            company_name=company_name,
            company_email=company_email,
            gst_number=gst_number,
            contact_person=contact_person,
            contact_number=contact_number,
            address=address,
            address_2=address_2,
            city=city,
            district=district,
            state=state,
            zip_code=zip_code,
            is_active=True
        )
        
        log_activity(user, "Dealer Customer Created", f"Created dealer customer {company_name} (ID: {customer_id})")
        messages.success(request, f"Customer contact {company_name} created successfully.")
        return redirect('dealer_customer_list')
    
    return render(request, 'companydetails/dealer_customer_form.html', {
        'title': 'Create Customer Contact',
        'button_text': 'Create Customer'
    })


@login_required
@user_passes_test(dealer_required)
def dealer_customer_edit(request, pk):
    """
    Edit an existing dealer customer contact record.
    """
    user = request.user
    
    if user.role != 'DEALER_ADMIN' or not user.company_relation:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    dealer = user.company_relation
    dealer_customer = get_object_or_404(DealerCustomer, pk=pk, dealer=dealer)
    
    if request.method == 'POST':
        # Update customer details
        dealer_customer.company_name = request.POST.get('company_name')
        dealer_customer.company_email = request.POST.get('company_email')
        dealer_customer.contact_person = request.POST.get('contact_person')
        dealer_customer.contact_number = request.POST.get('contact_number')
        dealer_customer.address = request.POST.get('address')
        dealer_customer.address_2 = request.POST.get('address_2', '')
        dealer_customer.city = request.POST.get('city')
        dealer_customer.district = request.POST.get('district', '')
        dealer_customer.state = request.POST.get('state')
        dealer_customer.zip_code = request.POST.get('zip_code')
        dealer_customer.gst_number = request.POST.get('gst_number', '')
        
        dealer_customer.save()
        
        log_activity(user, "Dealer Customer Updated", f"Updated dealer customer {dealer_customer.company_name}")
        messages.success(request, f"Customer contact {dealer_customer.company_name} updated successfully.")
        return redirect('dealer_customer_list')
    
    return render(request, 'companydetails/dealer_customer_form.html', {
        'customer': dealer_customer,
        'title': 'Edit Customer Contact',
        'button_text': 'Update Customer'
    })


@login_required
@user_passes_test(dealer_required)
def dealer_customer_delete(request, pk):
    """
    Delete a dealer customer contact record.
    """
    user = request.user
    
    if user.role != 'DEALER_ADMIN' or not user.company_relation:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    dealer = user.company_relation
    dealer_customer = get_object_or_404(DealerCustomer, pk=pk, dealer=dealer)
    
    if request.method == 'POST':
        company_name = dealer_customer.company_name
        email = dealer_customer.company_email
        
        # 1. Delete associated login accounts (matched by email)
        affected_users = UserAccount.objects.filter(email=email)
        user_count = affected_users.count()
        affected_users.delete()
        
        # 2. Delete specific mappings for this customer
        # Note: Devices themselves are kept but will be unassigned (null dealer_customer) 
        # because of on_delete=SET_NULL in configdetails.models.Device
        Mapping.objects.filter(dealer_customer=dealer_customer).delete()
        ButtonMapping.objects.filter(dealer_customer=dealer_customer).delete()
        
        # 3. Delete the customer record itself
        dealer_customer.delete()
        
        log_activity(user, "Dealer Customer Deep Deleted", 
                     f"Deleted dealer customer {company_name} and {user_count} associated login(s).")
        messages.success(request, f"Customer '{company_name}' and all associated data have been deleted successfully.")
    
    return redirect('dealer_customer_list')


@login_required
@user_passes_test(dealer_required)
def dealer_customer_toggle_status(request, pk):
    """
    Toggle active status of a dealer customer.
    """
    user = request.user
    
    if user.role != 'DEALER_ADMIN' or not user.company_relation:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    dealer = user.company_relation
    dealer_customer = get_object_or_404(DealerCustomer, pk=pk, dealer=dealer)
    
    if request.method == 'POST':
        dealer_customer.is_active = not dealer_customer.is_active
        dealer_customer.save()
        
        status = "Activated" if dealer_customer.is_active else "Deactivated"
        log_activity(user, "Dealer Customer Status Toggled", f"{status} dealer customer {dealer_customer.company_name}")
        messages.success(request, f"Customer contact {dealer_customer.company_name} {status.lower()} successfully.")
    
    return redirect('dealer_customer_list')
