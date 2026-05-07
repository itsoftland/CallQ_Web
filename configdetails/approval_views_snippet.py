# result/approvals/ views to be added to views.py

@login_required
def device_approval_list(request):
    """
    List devices with licence_status='Pending' for approval.
    """
    user = request.user
    
    # Filter based on role (similar to device_list)
    if user.role == "SUPER_ADMIN":
        pending_devices = Device.objects.filter(licence_status='Pending')
    elif user.role == "ADMIN":
        if user.assigned_state:
            pending_devices = Device.objects.filter(licence_status='Pending', company__state__in=user.assigned_state)
        else:
            pending_devices = Device.objects.none()
    elif user.role == "COMPANY_ADMIN":
        pending_devices = Device.objects.filter(licence_status='Pending', company=user.company_relation)
    elif user.role == "DEALER_ADMIN":
        if user.company_relation:
            # Dealer sees their own and their customers' pending devices
            pending_devices = Device.objects.filter(
                licence_status='Pending'
            ).filter(
                Q(company=user.company_relation) | 
                Q(company__parent_company=user.company_relation)
            )
        else:
            pending_devices = Device.objects.none()
    else:
        pending_devices = Device.objects.none()
        
    return render(request, 'configdetails/device_approval_list.html', {
        'pending_devices': pending_devices
    })

@login_required
def approve_device_request(request, device_id):
    if request.method == 'POST':
        device = get_object_or_404(Device, id=device_id)
        # Add permission check here if needed
        
        device.licence_status = 'Active'
        device.save()
        messages.success(request, f"Device {device.serial_number} approved successfully.")
        return redirect('device_approval_list')
    return redirect('device_approval_list')

@login_required
def reject_device_request(request, device_id):
    if request.method == 'POST':
        device = get_object_or_404(Device, id=device_id)
        # Add permission check here if needed
        
        serial = device.serial_number
        device.delete()
        messages.warning(request, f"Device request for {serial} rejected and removed.")
        return redirect('device_approval_list')
    return redirect('device_approval_list')
