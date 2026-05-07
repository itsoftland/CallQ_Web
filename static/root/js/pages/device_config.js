document.addEventListener('DOMContentLoaded', function () {
    // --- VIP Settings Logic ---
    const vipEnable = document.getElementById('vip_enable');
    const vipFrom = document.getElementById('vip_from');
    const vipTo = document.getElementById('vip_to');
    const vipCountFrom = document.getElementById('vip_count_from');
    const vipCountTo = document.getElementById('vip_count_to');

    if (vipEnable) {
        function toggleVipFields() {
            const isEnabled = vipEnable.checked;
            const fields = [vipFrom, vipTo, vipCountFrom, vipCountTo].filter(Boolean);
            fields.forEach(f => {
                f.disabled = !isEnabled;
                if (f.parentElement) f.parentElement.style.opacity = isEnabled ? '1' : '0.5';
            });
        }
        toggleVipFields();
        vipEnable.addEventListener('change', toggleVipFields);
    }

    // --- Token Dispenser Logic ---
    const dayWiseReset = document.getElementById('day_wise_reset');
    const resetTokenNumber = document.getElementById('reset_token_number');

    if (dayWiseReset && resetTokenNumber) {
        function toggleResetTokenNumber() {
            const enabled = dayWiseReset.checked;
            resetTokenNumber.disabled = !enabled;
            if (resetTokenNumber.parentElement) resetTokenNumber.parentElement.style.opacity = enabled ? '1' : '0.5';
        }
        toggleResetTokenNumber();
        dayWiseReset.addEventListener('change', toggleResetTokenNumber);
    }

    // --- Dynamic Keypad Inputs Logic ---
    const noOfKeypadDevInput = document.getElementById('no_of_keypad_dev');

    if (noOfKeypadDevInput) {
        // Initial setup based on current value (or default 1)
        updateKeypadInputs(noOfKeypadDevInput.value);

        // Listen to multiple events for robustness
        ['input', 'change', 'keyup'].forEach(eventType => {
            noOfKeypadDevInput.addEventListener(eventType, function () {
                updateKeypadInputs(this.value);
            });
        });

        function updateKeypadInputs(count) {
            count = parseInt(count);
            if (isNaN(count) || count < 1) count = 1;
            if (count > 5) {
                count = 5; // Max limit
                noOfKeypadDevInput.value = 5; // Enforce in UI
            }

            for (let i = 1; i <= 5; i++) {
                const group = document.getElementById(`keypad_group_${i}`);
                if (group) {
                    if (i <= count) {
                        group.style.display = 'block';
                    } else {
                        group.style.display = 'none';
                    }
                }
            }
        }
    }

    // --- Ads Preview Logic ---
    const adFilesInput = document.getElementById('ad_files');
    const adPreviewContainer = document.getElementById('ad_selection_preview');
    const previewTableBody = document.getElementById('preview_table_body');
    const previewModal = document.getElementById('adPreviewModal');
    const modalPreviewContainer = document.getElementById('modal_preview_container');
    const modalAdName = document.getElementById('modal_ad_name');

    let selectedFiles = [];

    if (adFilesInput && adPreviewContainer && previewTableBody) {
        adFilesInput.addEventListener('change', function (e) {
            const newFiles = Array.from(e.target.files);
            selectedFiles = [...selectedFiles, ...newFiles];
            updatePreview();
        });

        function updatePreview() {
            previewTableBody.innerHTML = '';

            if (selectedFiles.length === 0) {
                adPreviewContainer.classList.add('d-none');
                adFilesInput.value = '';
                return;
            }

            adPreviewContainer.classList.remove('d-none');

            const dataTransfer = new DataTransfer();

            selectedFiles.forEach((file, index) => {
                dataTransfer.items.add(file);

                const size = (file.size / 1024 / 1024).toFixed(2);
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="small align-middle text-truncate" style="max-width: 250px;">${file.name}</td>
                    <td class="small align-middle">${size} MB</td>
                    <td class="text-end text-nowrap">
                        <button type="button" class="btn btn-sm btn-outline-primary border-0 view-local-ad" data-index="${index}">
                            <i class="fas fa-eye me-1"></i>View
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-danger border-0 remove-file" data-index="${index}">
                            <i class="fas fa-times"></i>
                        </button>
                    </td>
                `;
                previewTableBody.appendChild(row);
            });

            adFilesInput.files = dataTransfer.files;

            // Handle removal
            document.querySelectorAll('.remove-file').forEach(btn => {
                btn.onclick = function () {
                    const idx = parseInt(this.getAttribute('data-index'));
                    selectedFiles.splice(idx, 1);
                    updatePreview();
                };
            });

            // Handle local preview
            document.querySelectorAll('.view-local-ad').forEach(btn => {
                btn.onclick = function () {
                    const idx = parseInt(this.getAttribute('data-index'));
                    const file = selectedFiles[idx];
                    const url = URL.createObjectURL(file);
                    showModalPreview(url, file.name, file.type);
                };
            });
        }
    }

    // --- Modal Preview Function ---
    function showModalPreview(url, name, type) {
        if (!modalPreviewContainer) return;

        modalPreviewContainer.innerHTML = '';
        modalAdName.textContent = name;

        if (type.startsWith('image/')) {
            const img = document.createElement('img');
            img.src = url;
            img.className = 'img-fluid shadow-sm rounded';
            img.style.maxHeight = '400px';
            modalPreviewContainer.appendChild(img);
        } else if (type.startsWith('video/')) {
            const video = document.createElement('video');
            video.src = url;
            video.controls = true;
            video.autoplay = true;
            video.className = 'w-100 shadow-sm rounded';
            video.style.maxHeight = '400px';
            modalPreviewContainer.appendChild(video);
        } else {
            // Backup for uploaded ads where we might not have MIME type
            const ext = name.split('.').pop().toLowerCase();
            if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) {
                const img = document.createElement('img');
                img.src = url;
                img.className = 'img-fluid shadow-sm rounded';
                img.style.maxHeight = '400px';
                modalPreviewContainer.appendChild(img);
            } else if (['mp4', 'webm', 'ogg', 'mov'].includes(ext)) {
                const video = document.createElement('video');
                video.src = url;
                video.controls = true;
                video.autoplay = true;
                video.className = 'w-100 shadow-sm rounded';
                video.style.maxHeight = '400px';
                modalPreviewContainer.appendChild(video);
            } else {
                modalPreviewContainer.innerHTML = '<div class="alert alert-secondary small m-0">Preview not available for this file type.</div>';
            }
        }

        const modal = new bootstrap.Modal(previewModal);
        modal.show();

        // Cleanup Object URL when modal is hidden (only if it was local)
        if (url.startsWith('blob:')) {
            previewModal.addEventListener('hidden.bs.modal', function handler() {
                URL.revokeObjectURL(url);
                previewModal.removeEventListener('hidden.bs.modal', handler);
            }, { once: true });
        }
    }

    // Handle clicks on existing uploaded ads
    document.querySelectorAll('.view-ad-btn').forEach(btn => {
        btn.onclick = function () {
            const url = this.getAttribute('data-url');
            const name = this.getAttribute('data-name');
            showModalPreview(url, name, ''); // Type empty, use extension fallback
        };
    });

    // --- Real-time Counter Visibility Logic ---
    const noOfCountersSelect = document.querySelector('select[name="no_of_counters"]');

    if (noOfCountersSelect) {
        noOfCountersSelect.addEventListener('change', function () {
            updateCounterVisibility(this.value);
        });

        function updateCounterVisibility(count) {
            count = parseInt(count);
            if (isNaN(count)) return;

            const cards = document.querySelectorAll('.counter-card');
            cards.forEach(card => {
                const index = parseInt(card.getAttribute('data-index'));
                if (index <= count) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        }

        // Run once on load to ensure initial state is correct
        updateCounterVisibility(noOfCountersSelect.value);
    }

    // --- Real-time Dispenser Visibility Logic (for TV devices) ---
    const noOfDispensersSelect = document.getElementById('no_of_dispensers_select') || document.querySelector('select[name="no_of_dispensers"]');

    if (noOfDispensersSelect) {
        function updateDispenserVisibility(count) {
            count = parseInt(count);
            if (isNaN(count) || count < 1) count = 1;
            if (count > 8) count = 8;

            const dropdowns = document.querySelectorAll('.dispenser-dropdown-wrapper');
            dropdowns.forEach(dropdown => {
                const index = parseInt(dropdown.getAttribute('data-dispenser-index'));
                if (index <= count) {
                    dropdown.style.display = 'block';
                } else {
                    dropdown.style.display = 'none';
                }
            });
        }

        noOfDispensersSelect.addEventListener('change', function () {
            updateDispenserVisibility(this.value);
        });

        // Run once on load to ensure initial state is correct
        updateDispenserVisibility(noOfDispensersSelect.value);
    }
});
