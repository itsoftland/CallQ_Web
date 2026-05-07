(function () {
  'use strict';

  const form = document.getElementById('customerForm');
  const alertArea = document.getElementById('formAlertArea');

  /* ---------- ALERT ---------- */
  function showAlert(message, type = 'success') {
    alertArea.innerHTML = `
      <div class="alert alert-${type} alert-dismissible fade show">
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      </div>`;
  }

  /* ---------- CSRF ---------- */
  function getCSRFToken() {
    return document.cookie
      .split('; ')
      .find(row => row.startsWith('csrftoken='))
      ?.split('=')[1];
  }

  /* ---------- SUBMIT ---------- */
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!form.checkValidity()) {
      form.classList.add('was-validated');
      return;
    }

    const payload = {
      company_name: document.getElementById('CustomerName').value.trim(),
      company_email: document.getElementById('CustomerEmail').value.trim(),
      gst_number: document.getElementById('GSTNumber').value.trim(),
      contact_person: document.getElementById('CustomerContactPerson').value.trim(),
      contact_number: document.getElementById('CustomerContact').value.trim(),
      address: document.getElementById('CustomerAddress').value.trim(),
      address_2: "", // optional / not in form
      city: document.getElementById('CustomerCity').value.trim(),
      state: document.getElementById('CustomerState').value.trim(),
      zip_code: document.getElementById('CustomerZip').value.trim()
    };

    console.log(payload);
    try {
      const response = await fetch('/api/create_customer/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error('Failed to create customer');
      }

      showAlert('Customer created successfully');

      setTimeout(() => {
        window.location.href = '/customer-list/';
      }, 1000);

    } catch (err) {
      showAlert(err.message, 'danger');
    }
  });

})();
