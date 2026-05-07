/* ---------- CSRF ---------- */
function getCSRFToken() {
  return document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
}

/* ---------- CONFIG FROM DJANGO ---------- */
function getAppConfig() {
  const configEl = document.getElementById('app-config');
  return {
    version: configEl?.dataset?.version || 'CallQ v1.0.0',
    projectName: configEl?.dataset?.project || 'CallQ'
  };
}

/* ---------- CONSTANTS ---------- */
const POLL_INTERVAL = 3000; // 3 seconds
const MAX_DURATION = 5 * 60 * 1000; // 5 minutes

/* ---------- FETCH CUSTOMER LIST ---------- */
async function fetchCustomers() {
  const loadingEl = document.getElementById('loading');
  const listEl = document.getElementById('customerList');
  const errorEl = document.getElementById('error');

  // show loader
  loadingEl.classList.remove('d-none');
  listEl.classList.add('d-none');
  errorEl.classList.add('d-none');

  try {
    const response = await fetch('/api/customer_list/', {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Failed to load customers');
    }

    renderCustomers(data.data);

    // ✅ SHOW TABLE, HIDE LOADER
    loadingEl.classList.add('d-none');
    listEl.classList.remove('d-none');

  } catch (err) {
    console.error(err);

    loadingEl.classList.add('d-none');
    errorEl.textContent = err.message;
    errorEl.classList.remove('d-none');
  }
}

function renderCustomers(customers) {
  const tbody = document.getElementById('customerTableBody');
  tbody.innerHTML = '';

  if (!customers.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="4" class="text-center">No customers found</td>
      </tr>`;
    return;
  }

  customers.forEach(c => {
    const tr = document.createElement('tr');
    tr.id = `customer-row-${c.id}`;

    tr.innerHTML = `
      <td>${c.company_id || '-'}</td>
      <td>${c.company_name || '-'}</td>
      <td>
        <span class="badge bg-secondary">
          ${c.verification_status || 'pending'}
        </span>
      </td>
      <td>
        <button class="btn btn-sm btn-primary"
          onclick='handleAuthenticate(${JSON.stringify(c)}, ${c.id})'
          ${c.verification_status === 'verified' ? 'disabled' : ''}>
          Authenticate
        </button>
      </td>
    `;

    tbody.appendChild(tr);
  });
}

async function handleAuthenticate(c, recordId) {
  try {
    let companyId = c.company_id;

    /* ---------- 1️⃣ REGISTER CUSTOMER ONLY IF NO COMPANY ID ---------- */
    if (!companyId) {
      const appConfig = getAppConfig();
      const payload = {
        DeviceModel: 'windows',
        DeviceIdentifier1: 'CallQ',
        PhoneNumber: c.contact_number || '',
        GSTNumber: c.gst_number || '123456',
        CustomerName: c.company_name,
        CustomerContactPerson: c.contact_person,
        CustomerAddress: c.address,
        CustomerCity: c.city,
        CustomerState: c.state,
        CustomerZip: c.zip_code,
        CustomerContact: c.contact_number,
        CustomerEmail: c.company_email,
        DeviceType: 1,
        Version: appConfig.version,
        ProjectName: appConfig.projectName
      };
      console.log(payload);
      const regRes = await fetch('/api/customer_register/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify(payload)
      });

      const regData = await regRes.json();
      if (!regRes.ok) throw new Error('Customer registration failed');
      console.log(regData);
      // ✅ GET COMPANY ID FROM REG RESPONSE
      companyId = regData.CustomerId;
      console.log(regData);

      const Payload = {
        company_id: regData.CustomerId
      }
      console.log(Payload);
      console.log(recordId);
      // ✅ SAVE REGISTRATION RESULT
      await fetch(`/api/customer-registration/save/${recordId}/`, {
        method: 'PATCH',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify(Payload)
      });
      console.log("company reg done");
    }
    /* ---------- 2️⃣ START AUTHENTICATION (ALWAYS) ---------- */
    pollAuthentication(companyId, recordId);

  } catch (err) {
    alert(err.message);
  }
}


/* ---------- POLLING ---------- */
function pollAuthentication(companyId, recordId) {
  const startTime = Date.now();

  const timer = setInterval(async () => {
    if (Date.now() - startTime > MAX_DURATION) {
      clearInterval(timer);
      updateRow(recordId, 'failed');
      return;
    }

    try {
      const authRes = await fetch('/api/customer_authentication/', {
        method: 'POST',
        credentials: 'same-origin', // ✅ REQUIRED
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ CustomerId: companyId })
      });

      const authData = await authRes.json();
      if (!authRes.ok) throw new Error('Authentication failed');

      console.log(authData);

      await fetch(`/api/customer-authentication/save/${companyId}/`,
        {
          method: 'PATCH',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
          },
          body: JSON.stringify(authData)
        });

      updateRow(recordId, authData.status);

      if (authData.status === 'approved' || authData.status === 'verified') {
        clearInterval(timer);
      }

    } catch (err) {
      console.error(err);
    }
  }, POLL_INTERVAL);
}

/* ---------- UPDATE UI ---------- */
function updateRow(recordId, status) {
  const row = document.getElementById(`customer-row-${recordId}`);
  if (!row) return;

  const badge = row.querySelector('.badge');

  badge.textContent = status;
  badge.className = `badge ${status === 'verified' || status === 'approved'
    ? 'bg-success'
    : 'bg-warning'
    }`;
}

/* ---------- INIT ---------- */
// ✅ FETCH CUSTOMER LIST ON PAGE LOAD
document.addEventListener('DOMContentLoaded', fetchCustomers);
