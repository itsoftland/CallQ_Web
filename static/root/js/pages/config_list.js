function filterConfigTable() {
    const searchInput = document.getElementById('searchInput').value.toLowerCase();
    const typeFilter = document.getElementById('deviceTypeFilter').value;
    const branchFilterEl = document.getElementById('branchFilter');
    const branchFilter = branchFilterEl ? branchFilterEl.value : '';

    const rows = document.querySelectorAll('#configTable tbody tr:not(.no-results)');

    rows.forEach(row => {
        const serial = row.getAttribute('data-serial').toLowerCase();
        const type = row.getAttribute('data-type');
        const branch = row.getAttribute('data-branch');

        const matchesSearch = serial.includes(searchInput);
        const matchesType = !typeFilter || type === typeFilter;
        const matchesBranch = !branchFilter || branch === branchFilter;

        if (matchesSearch && matchesType && matchesBranch) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

function clearConfigFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('deviceTypeFilter').value = '';
    const branchFilterEl = document.getElementById('branchFilter');
    if (branchFilterEl) {
        branchFilterEl.value = '';
    }
    filterConfigTable();
}
