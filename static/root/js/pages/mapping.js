function toggleKeypadInputs() {
    var num = document.getElementById('numKeypads').value;
    document.getElementById('keypad1_div').style.display = 'block';
    document.getElementById('keypad2_div').style.display = (num >= 2) ? 'block' : 'none';
    document.getElementById('keypad3_div').style.display = (num >= 3) ? 'block' : 'none';
    document.getElementById('keypad4_div').style.display = (num >= 4) ? 'block' : 'none';
}

async function fetchDevices() {
    const branchId = document.getElementById('branchSelect').value;
    const batchId = document.getElementById('batchSelect').value;

    // Clear existing
    const selects = ['tdSelect', 'tvSelect', 'bkSelect', 'ledSelect', 'kp1Select', 'kp2Select', 'kp3Select', 'kp4Select'];
    selects.forEach(id => {
        const sel = document.getElementById(id);
        if (sel) {
            sel.innerHTML = '<option value="">Loading...</option>';
            sel.disabled = true;
        }
    });

    if (!branchId) {
        selects.forEach(id => {
            const sel = document.getElementById(id);
            if (sel) {
                sel.innerHTML = '<option value="">-- Select Branch First --</option>';
            }
        });
        return;
    }

    try {
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        const csrf = csrfInput ? csrfInput.value : '';

        const response = await fetch('/config/api/mapping/devices/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf
            },
            body: JSON.stringify({
                branch_id: branchId,
                batch_id: batchId
            })
        });

        const data = await response.json();

        // Helper to populate
        const populate = (selId, items) => {
            const sel = document.getElementById(selId);
            if (sel) {
                sel.innerHTML = '<option value="">-- Select --</option>';
                items.forEach(item => {
                    const option = document.createElement('option');
                    option.value = item.serial_number;
                    option.textContent = item.serial_number;
                    sel.appendChild(option);
                });
                sel.disabled = false;
            }
        };

        populate('tvSelect', data.tvs);
        populate('tdSelect', data.token_dispensers);
        populate('bkSelect', data.brokers);
        populate('ledSelect', data.leds);
        populate('kp1Select', data.keypads);
        populate('kp2Select', data.keypads);
        populate('kp3Select', data.keypads);
        populate('kp4Select', data.keypads);

    } catch (error) {
        console.error('Error fetching devices:', error);
        selects.forEach(id => {
            const sel = document.getElementById(id);
            if (sel) {
                sel.innerHTML = '<option value="">Error Loading</option>';
            }
        });
    }
}
