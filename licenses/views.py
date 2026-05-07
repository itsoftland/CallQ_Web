from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from .models import Batch, License
from .serializers import BatchSerializer, LicenseSerializer
from callq_core.permissions import dealer_required, company_required
from callq_core.services import log_activity
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

class BatchViewSet(viewsets.ModelViewSet):
    """
    Manage License Batches.
    """
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer
    permission_classes = [IsAuthenticated] # detailed checks in get_queryset

    def get_queryset(self):
        user = self.request.user
        from companydetails.models import DealerCustomer
        from django.db.models import Q
        
        if user.role == 'SUPER_ADMIN':
            return Batch.objects.all()
        elif user.role == 'ADMIN':
            if user.assigned_state:
                return Batch.objects.filter(customer__state__in=user.assigned_state)
            return Batch.objects.none()
        elif user.role == 'DEALER_ADMIN':
            # Dealer sees batches for their child customers and dealer-customers
            return Batch.objects.filter(
                Q(customer__parent_company=user.company_relation) |
                Q(dealer_customer__dealer=user.company_relation)
            )
        elif user.role == 'COMPANY_ADMIN':
            # Customer sees their own batches
            return Batch.objects.filter(customer=user.company_relation)
        elif user.role == 'DEALER_CUSTOMER':
            # Dealer customer sees their own batches
            try:
                dealer_customer = DealerCustomer.objects.get(user=user)
                return Batch.objects.filter(dealer_customer=dealer_customer)
            except DealerCustomer.DoesNotExist:
                return Batch.objects.none()
        return Batch.objects.none()

    def perform_create(self, serializer):
        # Ensure company logic is respected if needed
        # For now trusting the payload validation or adding logic here
        batch = serializer.save()
        log_activity(self.request.user, "Batch Created", f"Batch {batch.name} for {batch.customer.company_name}")

class LicenseViewSet(viewsets.ModelViewSet):
    """
    Manage Individual Licenses.
    """
    queryset = License.objects.all()
    serializer_class = LicenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Similar logic to Batch
        if user.role == 'SUPER_ADMIN':
            return License.objects.all()
        elif user.role == 'ADMIN':
            if user.assigned_state:
                return License.objects.filter(batch__customer__state__in=user.assigned_state)
            return License.objects.none()
        elif user.role == 'DEALER_ADMIN':
             return License.objects.filter(batch__customer__parent_company=user.company_relation)
        elif user.role == 'COMPANY_ADMIN':
             return License.objects.filter(batch__customer=user.company_relation)
        return License.objects.none()

    @action(detail=False, methods=['post'], url_path='validate')
    def validate_license(self, request):
        """
        API for devices to validate their license key.
        Payload: { "license_key": "UUID...", "device_uid": "MAC/Serial" }
        """
        license_key = request.data.get('license_key')
        device_uid = request.data.get('device_uid')
        
        if not license_key:
             return Response({"error": "License key required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            lic = License.objects.get(license_key=license_key)
            
            if lic.status == License.Status.REVOKED:
                log_activity(None, "License Validation Failed", f"Revoked Key: {license_key} from {device_uid}")
                return Response({"status": "REVOKED"}, status=status.HTTP_403_FORBIDDEN)
            
            # If not active, activate it
            if lic.status == License.Status.INACTIVE:
                lic.status = License.Status.ACTIVE
                lic.device_uid = device_uid
                lic.activated_at = timezone.now()
                lic.save()
                log_activity(None, "License Activated", f"Key: {license_key} by {device_uid}")
            
            # If active, check if device_uid matches (if provided and strictly binding)
            if lic.status == License.Status.ACTIVE:
                if lic.device_uid and device_uid and lic.device_uid != device_uid:
                     log_activity(None, "License Validation Failed", f"Device Mismatch: {license_key} - Bound: {lic.device_uid}, Request: {device_uid}")
                     return Response({"status": "INVALID_DEVICE", "message": "License bound to another device"}, status=status.HTTP_403_FORBIDDEN)
            
            log_activity(None, "License Validated", f"Key: {license_key} by {device_uid}")
            
            return Response({
                "status": "VALID",
                "batch": lic.batch.name,
                "device_type": lic.device_type,
                "max_devices": {
                     "tvs": lic.batch.max_tvs,
                     "dispensers": lic.batch.max_dispensers,
                     # etc..
                }
            })
            
        except License.DoesNotExist:
            log_activity(None, "License Validation Failed", f"Invalid Key: {license_key}")
            return Response({"error": "Invalid License"}, status=status.HTTP_404_NOT_FOUND)

# Template Views
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from configdetails.models import Device

@login_required
def batch_page(request):
    user = request.user
    batches = Batch.objects.none()
    search_query = request.GET.get('search', '').strip()
    
    if user.role == 'SUPER_ADMIN':
        batches = Batch.objects.all().order_by('-created_at')
    elif user.role == 'ADMIN':
        if user.assigned_state:
            batches = Batch.objects.filter(customer__state__in=user.assigned_state).order_by('-created_at')
        else:
            batches = Batch.objects.none()
    elif user.role == 'DEALER_ADMIN':
        from django.db.models import Q
        if user.company_relation:
            batches = Batch.objects.filter(
                Q(customer=user.company_relation) |  # Their own batches
                Q(customer__parent_company=user.company_relation) |  # Child company batches
                Q(dealer_customer__dealer=user.company_relation)  # Dealer customer batches
            ).order_by('-created_at')
        else:
            batches = Batch.objects.none()
    elif user.role == 'COMPANY_ADMIN':
        batches = Batch.objects.filter(customer=user.company_relation).order_by('-created_at')
    elif user.role == 'DEALER_CUSTOMER':
        # Dealer customers see their own batches
        from companydetails.models import DealerCustomer
        try:
            dealer_customer = DealerCustomer.objects.get(user=user)
            batches = Batch.objects.filter(dealer_customer=dealer_customer).order_by('-created_at')
        except DealerCustomer.DoesNotExist:
            batches = Batch.objects.none()

    # Apply search filter
    if search_query:
        from django.db.models import Q
        batches = batches.filter(
            Q(name__icontains=search_query) |
            Q(customer__company_name__icontains=search_query) |
            Q(dealer_customer__company_name__icontains=search_query)
        )
    # Calculate stats for each batch
    batches_stats = []
    for batch in batches:
        # Count used devices linked to this batch
        # Assuming devices have foreign key 'batch'
        used_tvs = Device.objects.filter(batch=batch, device_type='TV').count()
        used_dispensers = Device.objects.filter(batch=batch, device_type='TOKEN_DISPENSER').count()
        used_keypads = Device.objects.filter(batch=batch, device_type='KEYPAD').count()
        used_brokers = Device.objects.filter(batch=batch, device_type='BROKER').count()
        used_leds = Device.objects.filter(batch=batch, device_type='LED').count()
        
        # Calculate raw values
        total_licenses = batch.max_tvs + batch.max_dispensers + batch.max_keypads + batch.max_brokers + batch.max_leds
        total_used = used_tvs + used_dispensers + used_keypads + used_brokers + used_leds
        
        # Calculate remaining (raw, can be negative if over-allocated)
        raw_remaining = {
            'tvs': batch.max_tvs - used_tvs,
            'dispensers': batch.max_dispensers - used_dispensers,
            'keypads': batch.max_keypads - used_keypads,
            'brokers': batch.max_brokers - used_brokers,
            'leds': batch.max_leds - used_leds
        }
        raw_total_remaining = sum(raw_remaining.values())
        
        # Check if any device type is over-allocated
        is_over_allocated = any(v < 0 for v in raw_remaining.values())
        
        # Calculate percentage (cap at 100 for display, but track actual for warnings)
        raw_percentage = int((total_used / total_licenses) * 100) if total_licenses > 0 else 0
        capped_percentage = min(raw_percentage, 100)
        
        batches_stats.append({
            'batch': batch,
            'usage': {
                'tvs': used_tvs,
                'dispensers': used_dispensers,
                'keypads': used_keypads,
                'brokers': used_brokers,
                'leds': used_leds
            },
            'remaining': {
                'tvs': max(0, raw_remaining['tvs']),
                'dispensers': max(0, raw_remaining['dispensers']),
                'keypads': max(0, raw_remaining['keypads']),
                'brokers': max(0, raw_remaining['brokers']),
                'leds': max(0, raw_remaining['leds'])
            },
            'total_licenses': total_licenses,
            'total_used': total_used,
            'total_remaining': max(0, raw_total_remaining),
            'usage_percentage': capped_percentage,
            'raw_percentage': raw_percentage,  # Actual percentage for display/warning
            'is_over_allocated': is_over_allocated  # Flag for UI warning
        })
    
    # Pagination - 8 rows per page
    page = request.GET.get('page', 1)
    paginator = Paginator(batches_stats, 8)
    try:
        batches_page = paginator.page(page)
    except PageNotAnInteger:
        batches_page = paginator.page(1)
    except EmptyPage:
        batches_page = paginator.page(paginator.num_pages)
    
    return render(request, 'licenses/batch_list.html', {
        'batches_stats': batches_page,
        'search_query': search_query,
    })

@login_required
def approve_batch(request, batch_id):
    """
    Approve a pending batch. Only for Super Admins.
    """
    if request.user.role not in ['SUPER_ADMIN', 'ADMIN']:
         # Simple permission check
         return redirect('batch_list')
         
    try:
        batch = Batch.objects.get(id=batch_id)
        if batch.status == Batch.Status.PENDING:
            batch.status = Batch.Status.ACTIVE
            batch.save()
            log_activity(request.user, "Batch Approved", f"Approved Batch {batch.name} for {batch.customer.company_name}")
    except Batch.DoesNotExist:
        pass
        
    return redirect('batch_list')


@login_required
def batch_download(request, batch_id):
    """
    Download batch details as PDF file.
    """
    from django.http import HttpResponse
    from configdetails.models import Device
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from io import BytesIO
    
    batch = get_object_or_404(Batch, id=batch_id)
    
    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, spaceAfter=20, textColor=colors.HexColor('#1a5f2a'))
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=14, spaceAfter=10, textColor=colors.HexColor('#333333'))
    
    # Title
    elements.append(Paragraph(f"Batch: {batch.name}", title_style))
    elements.append(Spacer(1, 10))
    
    # Batch Details
    elements.append(Paragraph("Batch Details", subtitle_style))
    
    batch_info = [
        ['Customer:', batch.customer.company_name if batch.customer else '-'],
        ['Customer ID:', batch.customer.company_id if batch.customer else '-'],
        ['Status:', batch.status],
        ['Created At:', batch.created_at.strftime('%Y-%m-%d %H:%M')],
    ]
    
    info_table = Table(batch_info, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # License Allocation
    elements.append(Paragraph("License Allocation", subtitle_style))
    
    used_tvs = Device.objects.filter(batch=batch, device_type='TV').count()
    used_dispensers = Device.objects.filter(batch=batch, device_type='TOKEN_DISPENSER').count()
    used_keypads = Device.objects.filter(batch=batch, device_type='KEYPAD').count()
    used_brokers = Device.objects.filter(batch=batch, device_type='BROKER').count()
    used_leds = Device.objects.filter(batch=batch, device_type='LED').count()
    
    license_data = [
        ['Device Type', 'Max Allowed', 'Used', 'Remaining'],
        ['TVs', str(batch.max_tvs), str(used_tvs), str(batch.max_tvs - used_tvs)],
        ['Token Dispensers', str(batch.max_dispensers), str(used_dispensers), str(batch.max_dispensers - used_dispensers)],
        ['Keypads', str(batch.max_keypads), str(used_keypads), str(batch.max_keypads - used_keypads)],
        ['Brokers', str(batch.max_brokers), str(used_brokers), str(batch.max_brokers - used_brokers)],
        ['LEDs', str(batch.max_leds), str(used_leds), str(batch.max_leds - used_leds)],
    ]
    
    license_table = Table(license_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    license_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5f2a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
    ]))
    elements.append(license_table)
    elements.append(Spacer(1, 20))
    
    # Devices
    devices = Device.objects.filter(batch=batch).order_by('device_type', 'serial_number')
    if devices.exists():
        elements.append(Paragraph("Devices Assigned to Batch", subtitle_style))
        
        device_data = [['Serial Number', 'Device Type', 'Model', 'Status', 'License Status']]
        for device in devices:
            device_data.append([
                device.serial_number,
                device.get_device_type_display(),
                device.device_model or '-',
                'Active' if device.is_active else 'Inactive',
                device.licence_status or '-',
            ])
        
        device_table = Table(device_data, colWidths=[1.8*inch, 1.3*inch, 1*inch, 1*inch, 1.2*inch])
        device_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5f2a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))
        elements.append(device_table)
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF content
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create response
    response = HttpResponse(content_type='application/pdf')
    customer_name = batch.customer.company_name.replace(' ', '_') if batch.customer else 'unknown'
    response['Content-Disposition'] = f'attachment; filename="batch_{batch.name}_{customer_name}.pdf"'
    response.write(pdf)
    
    log_activity(request.user, "Batch Downloaded", f"Downloaded batch {batch.name}")
    
    return response


@login_required
def purchase_batch(request):
    user = request.user
    
    # Determine the company based on role using helper
    company = None
    if user.role in ['SUPER_ADMIN', 'ADMIN']:
        # Admin purchasing for themselves or a specific tenant? 
        # For simplicity in V1.1 admin self-purchase or restrict. 
        # Assuming Admin belongs to a 'System' company or similar. 
        # Let's use user.company_relation for now.
        company = user.company_relation
    elif user.role in ['DEALER_ADMIN', 'COMPANY_ADMIN']:
        company = user.company_relation
        
    if not company:
         # Fallback or error if user has no company
         # Ideally redirect with error
         pass

    if request.method == 'POST':
        max_tvs = int(request.POST.get('max_tvs', 0))
        max_dispensers = int(request.POST.get('max_dispensers', 0))
        max_keypads = int(request.POST.get('max_keypads', 0))
        max_brokers = int(request.POST.get('max_brokers', 0))
        max_leds = int(request.POST.get('max_leds', 0))
        
        # Validation: check for negative numbers
        if any(x < 0 for x in [max_tvs, max_dispensers, max_keypads, max_brokers, max_leds]):
             # Add message error
             pass

        # Generate Batch Name
        # Get count of existing batches for this company
        current_count = Batch.objects.filter(customer=company).count()
        batch_name = f"B{current_count + 1}"
        
        # Create Batch (Default Status = PENDING)
        new_batch = Batch.objects.create(
            name=batch_name,
            customer=company,
            max_tvs=max_tvs,
            max_dispensers=max_dispensers,
            max_keypads=max_keypads,
            max_brokers=max_brokers,
            max_leds=max_leds,
            status=Batch.Status.PENDING # Explicitly PENDING for review
        )
        
        log_activity(user, "Batch Purchase Requested", f"Requested {batch_name}. Status: Pending.")
        
        return redirect('batch_list')

    return render(request, 'licenses/purchase_batch.html')


# ====== BATCH REQUEST VIEWS ======

@login_required
def request_batch(request):
    """
    Allow customers, dealers, and dealer-customers to request a new batch of licenses.
    """
    user = request.user
    from .models import BatchRequest
    from companydetails.models import DealerCustomer
    
    # Determine entity (Company or DealerCustomer)
    company = None
    dealer_customer = None
    existing_pending = None
    
    if user.role == 'DEALER_CUSTOMER':
        # Get dealer customer profile
        try:
            dealer_customer = DealerCustomer.objects.get(user=user)
            existing_pending = BatchRequest.objects.filter(
                dealer_customer=dealer_customer,
                status=BatchRequest.Status.PENDING
            ).first()
        except DealerCustomer.DoesNotExist:
            from django.contrib import messages
            messages.error(request, "No dealer customer profile found.")
            return redirect('dashboard')
    else:
        company = user.company_relation
        if not company:
            from django.contrib import messages
            messages.error(request, "No company associated with your account.")
            return redirect('dashboard')
        
        existing_pending = BatchRequest.objects.filter(
            requester=company,
            status=BatchRequest.Status.PENDING
        ).first()
    
    if request.method == 'POST':
        if existing_pending:
            from django.contrib import messages
            messages.warning(request, "You already have a pending batch request.")
            return redirect('batch_list')
        
        # Get requested device counts
        requested_tvs = int(request.POST.get('requested_tvs', 0))
        requested_dispensers = int(request.POST.get('requested_dispensers', 0))
        requested_keypads = int(request.POST.get('requested_keypads', 0))
        requested_brokers = int(request.POST.get('requested_brokers', 0))
        requested_leds = int(request.POST.get('requested_leds', 0))
        reason = request.POST.get('reason', '')
        
        # Validate at least one device requested
        if all(x == 0 for x in [requested_tvs, requested_dispensers, requested_keypads, requested_brokers, requested_leds]):
            from django.contrib import messages
            messages.error(request, "Please request at least one device.")
            return render(request, 'licenses/request_batch.html', {'existing_pending': existing_pending})
        
        # Determine requester type
        if dealer_customer:
            requester_type = BatchRequest.RequesterType.DEALER_CUSTOMER
            approval_message = "Awaiting dealer approval."
        elif company and company.company_type == 'DEALER':
            requester_type = BatchRequest.RequesterType.DEALER
            approval_message = "Awaiting admin approval."
        else:
            requester_type = BatchRequest.RequesterType.CUSTOMER
            approval_message = "Awaiting admin approval."
        
        # Create batch request
        batch_request = BatchRequest.objects.create(
            requester=company,
            dealer_customer=dealer_customer,
            requester_type=requester_type,
            requested_tvs=requested_tvs,
            requested_dispensers=requested_dispensers,
            requested_keypads=requested_keypads,
            requested_brokers=requested_brokers,
            requested_leds=requested_leds,
            reason=reason,
            status=BatchRequest.Status.PENDING
        )
        
        entity_name = dealer_customer.company_name if dealer_customer else company.company_name
        log_activity(user, "Batch Requested", f"Batch request #{batch_request.id} by {entity_name}")
        
        from django.contrib import messages
        messages.success(request, f"Batch request submitted successfully. {approval_message}")
        return redirect('batch_list')
    
    return render(request, 'licenses/request_batch.html', {'existing_pending': existing_pending})


@login_required
def batch_requests_list(request):
    """
    Admin and Dealer view to see batch requests.
    Admins see regular customer/dealer requests.
    Dealers see their dealer-customer requests.
    """
    user = request.user
    
    if user.role not in ['SUPER_ADMIN', 'ADMIN', 'DEALER_ADMIN']:
        return redirect('dashboard')
    
    from .models import BatchRequest
    from django.db.models import Q
    
    # Get filter from query params (default to showing all)
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '').strip()
    
    if user.role == 'SUPER_ADMIN':
        if status_filter == 'ALL' or not status_filter:
            requests = BatchRequest.objects.all()
        else:
            requests = BatchRequest.objects.filter(status=status_filter)
    elif user.role == 'ADMIN':
        if user.assigned_state:
            # Admins see regular customer/dealer requests (not dealer-customers)
            requests = BatchRequest.objects.filter(
                Q(requester__state__in=user.assigned_state) & Q(dealer_customer__isnull=True)
            )
            if status_filter and status_filter != 'ALL':
                requests = requests.filter(status=status_filter)
        else:
            requests = BatchRequest.objects.none()
    elif user.role == 'DEALER_ADMIN':
        if user.company_relation:
            # Dealers see requests from their dealer-customers AND their child companies
            requests = BatchRequest.objects.filter(
                Q(dealer_customer__dealer=user.company_relation) |  # Dealer-customer requests
                Q(requester__parent_company=user.company_relation)  # Child company requests
            )
            if status_filter and status_filter != 'ALL':
                requests = requests.filter(status=status_filter)
        else:
            requests = BatchRequest.objects.none()
    else:
        requests = BatchRequest.objects.none()

    # Apply search filter
    if search_query:
        requests = requests.filter(
            Q(requester__company_name__icontains=search_query) |
            Q(dealer_customer__company_name__icontains=search_query)
        )
    
    # Add stats (scoped to user's permissions)
    if user.role == 'SUPER_ADMIN':
        pending_count = BatchRequest.objects.filter(status=BatchRequest.Status.PENDING).count()
        approved_count = BatchRequest.objects.filter(status=BatchRequest.Status.APPROVED).count()
        rejected_count = BatchRequest.objects.filter(status=BatchRequest.Status.REJECTED).count()
    elif user.role == 'ADMIN' and user.assigned_state:
        base_qs = BatchRequest.objects.filter(requester__state__in=user.assigned_state, dealer_customer__isnull=True)
        pending_count = base_qs.filter(status=BatchRequest.Status.PENDING).count()
        approved_count = base_qs.filter(status=BatchRequest.Status.APPROVED).count()
        rejected_count = base_qs.filter(status=BatchRequest.Status.REJECTED).count()
    elif user.role == 'DEALER_ADMIN' and user.company_relation:
        base_qs = BatchRequest.objects.filter(
            Q(dealer_customer__dealer=user.company_relation) |
            Q(requester__parent_company=user.company_relation)
        )
        pending_count = base_qs.filter(status=BatchRequest.Status.PENDING).count()
        approved_count = base_qs.filter(status=BatchRequest.Status.APPROVED).count()
        rejected_count = base_qs.filter(status=BatchRequest.Status.REJECTED).count()
    else:
        pending_count = approved_count = rejected_count = 0
    
    # Pagination - 8 rows per page
    page = request.GET.get('page', 1)
    paginator = Paginator(list(requests), 8)
    try:
        requests_page = paginator.page(page)
    except PageNotAnInteger:
        requests_page = paginator.page(1)
    except EmptyPage:
        requests_page = paginator.page(paginator.num_pages)
    
    context = {
        'requests': requests_page,
        'status_filter': status_filter,
        'search_query': search_query,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    
    return render(request, 'licenses/batch_requests_list.html', context)


@login_required
def approve_batch_request(request, request_id):
    """
    Approve a batch request and create the corresponding batch.
    """
    user = request.user
    
    if user.role not in ['SUPER_ADMIN', 'ADMIN', 'DEALER_ADMIN']:
        return redirect('dashboard')
    
    from .models import BatchRequest
    from django.db.models import Sum
    
    try:
        batch_request = BatchRequest.objects.get(id=request_id)
        
        if batch_request.status != BatchRequest.Status.PENDING:
            from django.contrib import messages
            messages.warning(request, "This request has already been processed.")
            return redirect('batch_requests_list')
        
        # Get the requester entity
        company = batch_request.requester
        dealer_customer = batch_request.dealer_customer
        admin_notes = request.POST.get('admin_notes', '') if request.method == 'POST' else ''
        
        # --- DEALER-CUSTOMER APPROVAL (by Dealer) ---
        if dealer_customer and user.role == 'DEALER_ADMIN':
            dealer = user.company_relation
            if not dealer or batch_request.requester.parent_company != dealer:
                from django.contrib import messages
                messages.error(request, "Permission denied.")
                return redirect('batch_requests_list')
            
            # Check Dealer's remaining quota
            def get_val(qs, key): return qs.get(key) if qs.get(key) else 0
            
            total_q = Batch.objects.filter(customer=dealer).aggregate(
                t=Sum('max_tvs'), d=Sum('max_dispensers'), k=Sum('max_keypads'), b=Sum('max_brokers'), l=Sum('max_leds')
            )
            used_q = Batch.objects.filter(customer__parent_company=dealer).aggregate(
                t=Sum('max_tvs'), d=Sum('max_dispensers'), k=Sum('max_keypads'), b=Sum('max_brokers'), l=Sum('max_leds')
            )
            
            rem_t = get_val(total_q, 't') - get_val(used_q, 't')
            rem_d = get_val(total_q, 'd') - get_val(used_q, 'd')
            rem_k = get_val(total_q, 'k') - get_val(used_q, 'k')
            rem_b = get_val(total_q, 'b') - get_val(used_q, 'b')
            rem_l = get_val(total_q, 'l') - get_val(used_q, 'l')
            
            if (batch_request.requested_tvs > rem_t or batch_request.requested_dispensers > rem_d or 
                batch_request.requested_keypads > rem_k or batch_request.requested_brokers > rem_b or 
                batch_request.requested_leds > rem_l):
                from django.contrib import messages
                messages.error(request, "Insufficient license quota. Please request more from Admin.")
                return redirect('batch_requests_list')

            # Create the batch for dealer-customer
            current_count = Batch.objects.filter(dealer_customer=dealer_customer).count()
            batch_name = f"B{current_count + 1}"
            new_batch = Batch.objects.create(
                name=batch_name, dealer_customer=dealer_customer,
                max_tvs=batch_request.requested_tvs, max_dispensers=batch_request.requested_dispensers,
                max_keypads=batch_request.requested_keypads, max_brokers=batch_request.requested_brokers,
                max_leds=batch_request.requested_leds, status=Batch.Status.ACTIVE
            )
        
        # --- DEALER APPROVAL LOGIC (for child companies) ---
        elif user.role == 'DEALER_ADMIN' and company:
            # Dealer approval for child company (existing logic)
            dealer = user.company_relation
            if not dealer or company.parent_company != dealer:
                from django.contrib import messages
                messages.error(request, "Permission denied.")
                return redirect('batch_requests_list')
            
            # Check Dealer's remaining quota
            def get_val(qs, key): return qs.get(key) if qs.get(key) else 0
            
            total_q = Batch.objects.filter(customer=dealer).aggregate(
                t=Sum('max_tvs'), d=Sum('max_dispensers'), k=Sum('max_keypads'), b=Sum('max_brokers'), l=Sum('max_leds')
            )
            used_q = Batch.objects.filter(customer__parent_company=dealer).aggregate(
                t=Sum('max_tvs'), d=Sum('max_dispensers'), k=Sum('max_keypads'), b=Sum('max_brokers'), l=Sum('max_leds')
            )
            
            rem_t = get_val(total_q, 't') - get_val(used_q, 't')
            rem_d = get_val(total_q, 'd') - get_val(used_q, 'd')
            rem_k = get_val(total_q, 'k') - get_val(used_q, 'k')
            rem_b = get_val(total_q, 'b') - get_val(used_q, 'b')
            rem_l = get_val(total_q, 'l') - get_val(used_q, 'l')
            
            if (batch_request.requested_tvs > rem_t or batch_request.requested_dispensers > rem_d or 
                batch_request.requested_keypads > rem_k or batch_request.requested_brokers > rem_b or 
                batch_request.requested_leds > rem_l):
                from django.contrib import messages
                messages.error(request, "Insufficient license quota. Please request more from Admin.")
                return redirect('batch_requests_list')

            # Create the batch for customer
            current_count = Batch.objects.filter(customer=company).count()
            batch_name = f"B{current_count + 1}"
            new_batch = Batch.objects.create(
                name=batch_name, customer=company,
                max_tvs=batch_request.requested_tvs, max_dispensers=batch_request.requested_dispensers,
                max_keypads=batch_request.requested_keypads, max_brokers=batch_request.requested_brokers,
                max_leds=batch_request.requested_leds, status=Batch.Status.ACTIVE
            )
        
        # --- ADMIN APPROVAL LOGIC ---
        else:
            # Refresh Authentication from API
            from callq_core.services import LicenseManagementService
            if not company or not company.company_id:
                from django.contrib import messages
                messages.error(request, "Company has no API Customer ID. Validate company first.")
                return redirect('batch_requests_list')
                
            api_data = LicenseManagementService.authenticate_product(company.company_id)
            if not api_data or api_data.get('error'):
                from django.contrib import messages
                messages.error(request, f"API Refresh failed: {api_data.get('error') if api_data else 'Unknown error'}")
                return redirect('batch_requests_list')
            
            # Calculate differences against sum of existing batches
            from django.db.models import Sum
            existing_sums = Batch.objects.filter(customer=company).aggregate(
                t=Sum('max_tvs'), d=Sum('max_dispensers'), k=Sum('max_keypads'),
                b=Sum('max_brokers'), l=Sum('max_leds')
            )
            
            def p_int(v): return int(v) if v else 0
            def get_s(k): return existing_sums.get(k) or 0
            
            diff_t = p_int(api_data.get('NoofTelevisiondevices')) - get_s('t')
            diff_d = p_int(api_data.get('NoofTokenDispensors')) - get_s('d')
            diff_k = p_int(api_data.get('NoofKeypaddevices')) - get_s('k')
            diff_b = p_int(api_data.get('NoofBrokerdevices')) - get_s('b')
            diff_l = p_int(api_data.get('NoofLeddevices')) - get_s('l')
            
            if diff_t <= 0 and diff_d <= 0 and diff_k <= 0 and diff_b <= 0 and diff_l <= 0:
                 from django.contrib import messages
                 messages.warning(request, "No new device licenses found in the API refresh (compared to existing batches).")
                 return redirect('batch_requests_list')

            # Update company counts
            from companydetails.views import sync_company_license_data
            sync_company_license_data(company, api_data, user)
            
            # Get the newly created batch (sync_company_license_data creates it)
            new_batch = Batch.objects.filter(customer=company).order_by('-created_at').first()
            batch_name = new_batch.name if new_batch else "-"

        # Common Update Logic
        batch_request.status = BatchRequest.Status.APPROVED
        batch_request.reviewed_by = user
        batch_request.reviewed_at = timezone.now()
        batch_request.admin_notes = admin_notes
        batch_request.approved_batch = new_batch
        batch_request.save()
        
        entity_name = dealer_customer.company_name if dealer_customer else company.company_name
        log_activity(user, "Batch Request Approved", f"Approved request #{batch_request.id} for {entity_name}. Batch: {batch_name}.")
        from django.contrib import messages
        messages.success(request, f"Batch request approved. Batch {batch_name} created.")
        
    except BatchRequest.DoesNotExist:
        from django.contrib import messages
        messages.error(request, "Batch request not found.")
    
    return redirect('batch_requests_list')


@login_required
def reject_batch_request(request, request_id):
    """
    Reject a batch request.
    """
    user = request.user
    
    if user.role not in ['SUPER_ADMIN', 'ADMIN', 'DEALER_ADMIN']:
        return redirect('dashboard')
    
    from .models import BatchRequest
    
    try:
        batch_request = BatchRequest.objects.get(id=request_id)
        
        if user.role == 'DEALER_ADMIN':
            if not user.company_relation or batch_request.requester.parent_company != user.company_relation:
                from django.contrib import messages
                messages.error(request, "Permission denied.")
                return redirect('batch_requests_list')
        
        if batch_request.status != BatchRequest.Status.PENDING:
            from django.contrib import messages
            messages.warning(request, "This request has already been processed.")
            return redirect('batch_requests_list')
        
        # Get admin notes from POST if provided
        admin_notes = request.POST.get('admin_notes', '') if request.method == 'POST' else ''
        
        # Update the request
        batch_request.status = BatchRequest.Status.REJECTED
        batch_request.reviewed_by = user
        batch_request.reviewed_at = timezone.now()
        batch_request.admin_notes = admin_notes
        batch_request.save()
        
        log_activity(user, "Batch Request Rejected", f"Rejected request #{batch_request.id} for {batch_request.requester.company_name}.")
        
        from django.contrib import messages
        messages.success(request, f"Batch request rejected.")
        
    except BatchRequest.DoesNotExist:
        from django.contrib import messages
        messages.error(request, "Batch request not found.")
    
    return redirect('batch_requests_list')

