// Main JavaScript for Maintenance Help Desk

document.addEventListener('DOMContentLoaded', function() {
    console.log('main.js loaded successfully');
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                event.preventDefault();
            }
        });
    });

    // Auto-refresh dashboard data every 30 seconds
    if (window.location.pathname === '/mrwr/dashboard') {
        setInterval(function() {
            // You can implement AJAX refresh here if needed
            console.log('Dashboard auto-refresh check');
        }, 30000);
    }

    // Priority color coding for table rows
    const priorityRows = document.querySelectorAll('tr[data-priority]');
    priorityRows.forEach(function(row) {
        const priority = row.getAttribute('data-priority');
        row.classList.add('priority-' + priority);
    });

    // Search functionality for tables
    const searchInputs = document.querySelectorAll('.table-search');
    searchInputs.forEach(function(input) {
        input.addEventListener('keyup', function() {
            const searchTerm = this.value.toLowerCase();
            const table = this.closest('.table-responsive').querySelector('table');
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(function(row) {
                const text = row.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    });

    // Modal form handling
    const modalForms = document.querySelectorAll('.modal form');
    modalForms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                // Skip processing state for email configuration and VT machine forms
                if (form.action.includes('email_config') || submitButton.innerHTML.includes('Configuration') ||
                    form.action.includes('vt_machine') || submitButton.innerHTML.includes('VT Machine') ||
                    submitButton.innerHTML.includes('Add VT Machine') || submitButton.innerHTML.includes('Update VT Machine') ||
                    form.action.includes('take_back_ticket')) { /* Added condition for take_back_ticket */
                    console.log('Email configuration/VT Machine/Take Back modal form - no processing state');
                    return; // Don't add processing state for these forms
                }
                
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Updating...';
            }
        });
    });

    // Event delegation for reassign button clicks
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('reassign-btn')) {
            event.preventDefault(); // Prevent default button action (form submission)
            const reassignBtn = event.target;
            const form = reassignBtn.closest('.reassign-form');
            
            if (form) {
                const newAdminSelect = form.querySelector('select[name="new_admin"]');
                console.log('Reassign button clicked via event delegation. Selected admin ID:', newAdminSelect ? newAdminSelect.value : 'N/A');
                
                reassignBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
                reassignBtn.disabled = true;
                
                // Manually submit the form after a short delay to allow UI update
                setTimeout(() => {
                    form.submit();
                }, 100);
            }
        }
    });

    // Status badge click handlers
    const statusBadges = document.querySelectorAll('.badge[data-status]');
    statusBadges.forEach(function(badge) {
        badge.addEventListener('click', function() {
            const status = this.getAttribute('data-status');
            const ticketId = this.getAttribute('data-ticket-id');
            const ticketType = this.getAttribute('data-ticket-type');
            
            // You can implement quick status update here
            console.log('Quick status update:', { status, ticketId, ticketType });
        });
    });

    // Print functionality
    const printButtons = document.querySelectorAll('.print-btn');
    printButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            window.print();
        });
    });

    // Copy to clipboard functionality
    const copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            const text = this.getAttribute('data-copy');
            navigator.clipboard.writeText(text).then(function() {
                // Show success message
                const originalText = button.innerHTML;
                button.innerHTML = '<i class="fas fa-check"></i> Copied!';
                setTimeout(function() {
                    button.innerHTML = originalText;
                }, 2000);
            });
        });
    });

    // Loading states for buttons
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            const form = this.closest('form');
            if (form && form.checkValidity()) {
                // Skip processing state for close, approve, delete, email configuration, VT machine, and electrical ticket buttons
                if (this.classList.contains('close-btn') || this.classList.contains('approve-btn') || this.classList.contains('delete-btn') ||
                    form.classList.contains('close-form') || form.classList.contains('approve-form') || form.classList.contains('delete-form') ||
                    this.innerHTML.includes('Close') || form.action.includes('close_ticket') ||
                    this.innerHTML.includes('Approve') || form.action.includes('approve_ticket') ||
                    this.innerHTML.includes('Delete') || form.action.includes('delete_ticket') ||
                    form.action.includes('email_config') || this.innerHTML.includes('Configuration') ||
                    form.action.includes('vt_machine') || this.innerHTML.includes('VT Machine') ||
                    this.innerHTML.includes('Add VT Machine') || this.innerHTML.includes('Update VT Machine') ||
                    form.action.includes('raise_ticket/electrical') || this.innerHTML.includes('Submit Ticket') ||
                    (form.action.includes('take_back_ticket') && this.classList.contains('take-back-btn'))) { /* Refined condition for Take Back button */
                    console.log('Close/Approve/Delete/Email Config/VT Machine/Electrical Ticket/Take Back button clicked - no processing state');
                    return; // Don't add processing state for these buttons
                }
                
                // For login forms, handle differently
                if (form.action.includes('login') || window.location.pathname === '/mrwr/login') {
                    // Show processing state but don't disable button yet
                    const originalText = this.innerHTML;
                    this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
                    
                    // Disable button after a short delay to allow form submission
                    setTimeout(() => {
                        this.disabled = true;
                    }, 100);
                    
                    // Re-enable button after a delay in case of errors
                    setTimeout(() => {
                        this.disabled = false;
                        this.innerHTML = originalText;
                    }, 5000);
                    
                    console.log('Login form submitting...');
                    // Let the form submit naturally - don't prevent default
                } else if (window.location.pathname === '/mrwr/manager/add_user') {
                    // For Add User form, show processing but don't interfere
                    const originalText = this.innerHTML;
                    this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Adding User...';
                    
                    // Don't disable button to allow form submission
                    console.log('Add User form submitting...');
                    
                    // Re-enable button after a delay in case of errors
                    setTimeout(() => {
                        this.innerHTML = originalText;
                    }, 5000);
                } else {
                    // For other forms, disable immediately
                    this.disabled = true;
                    const originalText = this.innerHTML;
                    this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
                    
                    // Re-enable button after a delay in case of errors
                    setTimeout(() => {
                        this.disabled = false;
                        this.innerHTML = originalText;
                    }, 5000);
                }
            }
        });
    });

    // Character counter for textareas
    const textareas = document.querySelectorAll('textarea[data-max-length]');
    textareas.forEach(function(textarea) {
        const maxLength = parseInt(textarea.getAttribute('data-max-length'));
        const counter = document.createElement('small');
        counter.className = 'text-muted';
        counter.style.float = 'right';
        textarea.parentNode.appendChild(counter);
        
        function updateCounter() {
            const remaining = maxLength - textarea.value.length;
            counter.textContent = remaining + ' characters remaining';
            if (remaining < 0) {
                counter.className = 'text-danger';
            } else {
                counter.className = 'text-muted';
            }
        }
        
        textarea.addEventListener('input', updateCounter);
        updateCounter();
    });

    // Smooth scrolling for anchor links
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(function(link) {
        link.addEventListener('click', function(event) {
            event.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(event) {
        // Ctrl/Cmd + K for search
        if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
            event.preventDefault();
            const searchInput = document.querySelector('.table-search');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Escape to close modals
        if (event.key === 'Escape') {
            const openModals = document.querySelectorAll('.modal.show');
            openModals.forEach(function(modal) {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) {
                    bsModal.hide();
                }
            });
        }
    });

    // Initialize fade-in animations
    const fadeElements = document.querySelectorAll('.fade-in');
    fadeElements.forEach(function(element) {
        element.style.opacity = '0';
        element.style.transform = 'translateY(10px)';
        
        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.style.transition = 'opacity 0.3s ease-in-out, transform 0.3s ease-in-out';
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                    observer.unobserve(entry.target);
                }
            });
        });
        
        observer.observe(element);
    });
});

// Utility functions
function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    // Add to toast container
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    toastContainer.appendChild(toast);
    
    // Show toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove from DOM after hiding
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function formatPriority(priority) {
    const priorityMap = {
        'low': { class: 'info', icon: 'fas fa-arrow-down' },
        'medium': { class: 'warning', icon: 'fas fa-minus' },
        'high': { class: 'danger', icon: 'fas fa-arrow-up' }
    };
    
    const config = priorityMap[priority] || priorityMap['medium'];
    return `<span class="badge bg-${config.class}"><i class="${config.icon}"></i> ${priority.charAt(0).toUpperCase() + priority.slice(1)}</span>`;
}

function formatStatus(status) {
    const statusMap = {
        'open': { class: 'success', icon: 'fas fa-circle' },
        'in_progress': { class: 'warning', icon: 'fas fa-clock' },
        'closed': { class: 'secondary', icon: 'fas fa-check-circle' }
    };
    
    const config = statusMap[status] || statusMap['open'];
    const displayStatus = status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
    return `<span class="badge bg-${config.class}"><i class="${config.icon}"></i> ${displayStatus}</span>`;
}
