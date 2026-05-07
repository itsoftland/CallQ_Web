// Initialize Unified Filtering with Combinatorial Filters
document.addEventListener('DOMContentLoaded', () => {
    window.initTableFilter({
        searchInputId: 'searchInput',
        tableSelector: '.device-table',
        rowSelector: 'tbody tr',
        filters: [
            { id: 'typeFilter', attr: 'data-type' },
            { id: 'statusFilter', attr: 'data-status' }
        ]
    });
});
