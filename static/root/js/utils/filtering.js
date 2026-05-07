/**
 * CallQ Unified Table Filtering Utility
 * 
 * Provides real-time searching and filtering for tables with support for:
 * - Text search (case-insensitive)
 * - Attribute-based filtering (data-status, data-type, etc.)
 * - Combinatorial logic (AND)
 * - Empty state handling
 * - Multi-table support
 * - Batch wrapper visibility (hides empty batches)
 */

class TableFilter {
    constructor(options = {}) {
        this.searchInput = document.getElementById(options.searchInputId || 'searchInput');
        this.tableSelector = options.tableSelector || '.table';
        this.rowSelector = options.rowSelector || 'tbody tr';
        this.filters = options.filters || []; // Array of { id: 'filterId', attr: 'data-status' }
        this.emptyRowId = options.emptyRowId || 'noResultsRow';
        this.batchWrapperSelector = options.batchWrapperSelector || '.batch-wrapper';
        this.globalEmptyId = 'globalNoResultsRow';

        this.init();
    }

    init() {
        if (this.searchInput) {
            this.searchInput.addEventListener('input', () => this.applyFilters());
        }

        this.filters.forEach(f => {
            const el = document.getElementById(f.id);
            if (el) {
                el.addEventListener('change', () => this.applyFilters());
            }
        });

        // Initial apply
        this.applyFilters();
    }

    applyFilters() {
        const searchValue = this.searchInput ? this.searchInput.value.toLowerCase().trim() : '';
        const activeFilters = this.filters.map(f => {
            const el = document.getElementById(f.id);
            return {
                attr: f.attr,
                value: el ? el.value : ''
            };
        }).filter(f => f.value !== '');

        const tables = document.querySelectorAll(this.tableSelector);
        let totalVisibleCount = 0;

        tables.forEach(table => {
            const rows = table.querySelectorAll(this.rowSelector);
            let visibleCount = 0;

            rows.forEach(row => {
                // Skip empty state row if it exists in the table
                if (row.id === this.emptyRowId) return;

                const text = row.textContent.toLowerCase();
                const matchesSearch = !searchValue || text.includes(searchValue);

                const matchesFilters = activeFilters.every(f => {
                    const rowValue = row.getAttribute(f.attr) || '';
                    return rowValue === f.value;
                });

                if (matchesSearch && matchesFilters) {
                    row.style.display = '';
                    visibleCount++;
                } else {
                    row.style.display = 'none';
                }
            });

            // Track total visible across all tables
            totalVisibleCount += visibleCount;

            // Hide/show the batch wrapper based on visibility
            this.toggleBatchWrapper(table, visibleCount);
        });

        // Handle global empty state (show single message when all batches are empty)
        this.toggleGlobalEmptyState(totalVisibleCount);
    }

    toggleBatchWrapper(table, visibleCount) {
        // Find the parent batch wrapper
        const batchWrapper = table.closest(this.batchWrapperSelector);

        if (batchWrapper) {
            if (visibleCount === 0) {
                batchWrapper.style.display = 'none';
            } else {
                batchWrapper.style.display = '';
            }
        }
    }

    toggleGlobalEmptyState(totalVisibleCount) {
        // Look for an existing global empty state element
        let globalEmptyRow = document.getElementById(this.globalEmptyId);

        // Find the container where tables/batches are located
        const contentArea = document.querySelector(this.batchWrapperSelector)?.parentElement;

        if (totalVisibleCount === 0) {
            if (!globalEmptyRow && contentArea) {
                globalEmptyRow = document.createElement('div');
                globalEmptyRow.id = this.globalEmptyId;
                globalEmptyRow.className = 'card';
                globalEmptyRow.innerHTML = `
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-hover align-middle mb-0">
                                <tbody>
                                    <tr>
                                        <td colspan="6" class="text-center py-5">
                                            <div class="text-muted opacity-50 mb-3">
                                                <i class="fas fa-search fa-3x"></i>
                                            </div>
                                            <p class="h6 text-secondary">No results match your filters</p>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
                contentArea.appendChild(globalEmptyRow);
            } else if (globalEmptyRow) {
                globalEmptyRow.style.display = '';
            }
        } else if (globalEmptyRow) {
            globalEmptyRow.style.display = 'none';
        }
    }
}

// Global initialization helper
window.initTableFilter = (options) => new TableFilter(options);

