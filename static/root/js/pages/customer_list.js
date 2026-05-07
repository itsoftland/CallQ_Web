// Initialize Unified Filtering
document.addEventListener('DOMContentLoaded', () => {
    window.initTableFilter({
        searchInputId: 'searchInput',
        tableSelector: '#customerTable',
        rowSelector: 'tbody tr'
    });
});

async function authenticateAndPollSecure(button, companyDbId, externalCustomerId) {
    // Allow auto-registration flow where externalCustomerId might be null initially

    const icon = button.querySelector('i');
    const originalClass = icon.className;
    // Change icon to spinner
    icon.className = 'fas fa-spinner fa-spin';
    button.disabled = true;


    try {
        const authUrl = `${window.ajaxUrls.authenticateCustomer}${companyDbId}/`;
        const response = await fetch(authUrl, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            }
        });

        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
            const text = await response.text();
            console.error("Expected JSON but got:", text.substring(0, 200)); // Log first 200 chars
            throw new Error(`Server returned non-JSON response (Status ${response.status}). Valid session?`);
        }

        const data = await response.json();


        if (data.error) {
            throw new Error(data.error);
        }

        // Check if immediately approved
        if (data.Authenticationstatus === 'Approved' || data.Authenticationstatus === 'Success') {
            updateRow(companyDbId, data);
            return;
        }

        // Step 2: Start Polling (if status is Pending/Waiting)
        let attempts = 0;
        const maxAttempts = 100; // 5 minutes / 3 seconds = 100 attempts

        const pollInterval = setInterval(async () => {
            attempts++;
            if (attempts > maxAttempts) {
                clearInterval(pollInterval);
                icon.className = originalClass; // Revert icon
                button.disabled = false; // Re-enable button
                alert('Authentication timed out. Please try again.');
                return;
            }

            try {
                const statusUrl = `${window.ajaxUrls.checkCustomerStatus}${companyDbId}/`;
                const statusResponse = await fetch(statusUrl, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': 'application/json'
                    }
                });

                const contentType = statusResponse.headers.get("content-type");
                if (!contentType || !contentType.includes("application/json")) {
                    console.error("Polling received non-JSON response:", statusResponse.status);
                    return; // Skip this poll attempt
                }

                const statusData = await statusResponse.json();


                if (statusData.authentication_status === 'Approved' || statusData.authentication_status === 'Success' || statusData.status_text === 'Approved') {
                    clearInterval(pollInterval);
                    updateRow(companyDbId, statusData);
                }
            } catch (e) {
                console.error('Polling error:', e);
            }
        }, 3000);

    } catch (error) {
        console.error('Authentication Flow Error:', error);
        icon.className = originalClass;
        button.disabled = false;
        alert(`Error: ${error.message || 'An error occurred'}`);
    }
}

async function refreshCustomerAuth(button, companyDbId, externalCustomerId) {
    const icon = button.querySelector('i');
    const originalClass = icon.className;
    // Change icon to spinner
    icon.className = 'fas fa-spinner fa-spin';
    button.disabled = true;

    try {
        const authUrl = `${window.ajaxUrls.authenticateCustomer}${companyDbId}/`;
        const response = await fetch(authUrl, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            }
        });

        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
            const text = await response.text();
            console.error("Expected JSON but got:", text.substring(0, 200));
            throw new Error(`Server returned non-JSON response (Status ${response.status}). Valid session?`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Update row with latest data
        updateRow(companyDbId, data);
        
        // Revert icon
        icon.className = originalClass;
        button.disabled = false;

    } catch (error) {
        console.error('Refresh Authentication Error:', error);
        icon.className = originalClass;
        button.disabled = false;
        alert(`Error: ${error.message || 'An error occurred while refreshing authentication'}`);
    }
}

function updateRow(companyId, data) {
    const statusSpan = document.getElementById(`status-${companyId}`);
    const licenseSpan = document.getElementById(`licenses-${companyId}`);
    const actionBtn = document.querySelector(`.authenticate-btn[data-company-id="${companyId}"]`);

    // Determine authentication status from data
    const authStatus = data.Authenticationstatus || data.authentication_status || data.status_text || '';
    const statusText = data.status_text || getStatusText(authStatus);
    const statusClass = getStatusClass(authStatus, statusText);

    // Update status span
    if (statusSpan) {
        statusSpan.textContent = statusText;
        statusSpan.className = `badge ${statusClass}`;
    }

    // Update license span
    if (licenseSpan) {
        const usedLicenses = data.used_licenses || 0;
        const totalLicenses = data.total_licenses || data.NumberOfLicence || data.number_of_licence || 0;
        licenseSpan.textContent = `${usedLicenses}/${totalLicenses}`;
    }

    // Update authenticate button if status changed to Approved
    if (actionBtn) {
        if (authStatus === 'Approved' || authStatus === 'Success' || statusText === 'Approved') {
            actionBtn.disabled = true;
            actionBtn.innerHTML = '<i class="fas fa-check-circle"></i>';
            actionBtn.className = 'btn btn-outline-secondary btn-sm';
            actionBtn.onclick = null;
        } else {
            // Re-enable if status is not approved
            actionBtn.disabled = false;
            actionBtn.innerHTML = '<i class="fas fa-shield-alt"></i>';
            actionBtn.className = 'btn btn-outline-primary btn-sm';
        }
    }
}

function getStatusText(authStatus) {
    if (!authStatus) return 'Pending';
    
    const status = authStatus.toString().toLowerCase();
    if (status === 'approved' || status === 'success' || status === 'approve') {
        return 'Approved';
    } else if (status.includes('waiting') || status.includes('pending')) {
        return 'Pending';
    } else if (status.includes('expired')) {
        return 'Expired';
    } else {
        return authStatus;
    }
}

function getStatusClass(authStatus, statusText) {
    const status = (authStatus || statusText || '').toString().toLowerCase();
    
    if (status === 'approved' || status === 'success' || status === 'approve') {
        return 'bg-success';
    } else if (status.includes('expired')) {
        return 'bg-danger';
    } else if (status.includes('waiting') || status.includes('pending')) {
        return 'bg-warning text-dark';
    } else {
        return 'bg-warning text-dark';
    }
}
