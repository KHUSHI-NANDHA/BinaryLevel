// Main JavaScript for LocalLink

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Form validation (exclude auth forms to prevent interference)
    const forms = document.querySelectorAll('.needs-validation:not([action*="login"]):not([action*="register"])');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Loading states for buttons - disabled to prevent auth form interference
    // const submitButtons = document.querySelectorAll('button[type="submit"]');
    // submitButtons.forEach(button => {
    //     button.addEventListener('click', function() {
    //         if (this.form && this.form.checkValidity()) {
    //             this.innerHTML = '<span class="loading"></span> Processing...';
    //             this.disabled = true;
    //         }
    //     });
    // });

    // Dynamic pricing calculator for booking
    const hourlyRateInput = document.querySelector('#hourly_rate');
    const durationSelect = document.querySelector('#duration');
    const totalCostDisplay = document.querySelector('#total_cost');

    if (hourlyRateInput && durationSelect && totalCostDisplay) {
        function calculateTotal() {
            const rate = parseFloat(hourlyRateInput.value) || 0;
            const duration = parseInt(durationSelect.value) || 0;
            const total = rate * duration;
            totalCostDisplay.textContent = `$${total.toFixed(2)}`;
        }

        hourlyRateInput.addEventListener('input', calculateTotal);
        durationSelect.addEventListener('change', calculateTotal);
    }

    // Image preview for file uploads
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const preview = document.querySelector(`#${this.dataset.preview}`);
                    if (preview) {
                        preview.src = e.target.result;
                        preview.style.display = 'block';
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    });

    // Search functionality
    const searchInput = document.querySelector('#search_locals');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const localCards = document.querySelectorAll('.local-card');
            
            localCards.forEach(card => {
                const text = card.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }

    // Filter functionality
    const filterButtons = document.querySelectorAll('.filter-btn');
    const filterableItems = document.querySelectorAll('.filterable-item');

    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            const filter = this.dataset.filter;
            
            // Update active button
            filterButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            
            // Filter items
            filterableItems.forEach(item => {
                if (filter === 'all' || item.dataset.category === filter) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    });

    // Rating stars
    const ratingStars = document.querySelectorAll('.rating-star');
    ratingStars.forEach(star => {
        star.addEventListener('click', function() {
            const rating = parseInt(this.dataset.rating);
            const ratingInput = document.querySelector('#rating');
            
            if (ratingInput) {
                ratingInput.value = rating;
            }
            
            // Update star display
            ratingStars.forEach((s, index) => {
                if (index < rating) {
                    s.classList.add('text-warning');
                } else {
                    s.classList.remove('text-warning');
                }
            });
        });
    });

    // Confirmation dialogs
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this item?')) {
                e.preventDefault();
            }
        });
    });

    // Copy to clipboard functionality
    const copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const textToCopy = this.dataset.copy;
            navigator.clipboard.writeText(textToCopy).then(() => {
                // Show success message
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-check"></i> Copied!';
                this.classList.add('btn-success');
                
                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.classList.remove('btn-success');
                }, 2000);
            });
        });
    });

    // Real-time notifications
    if ('Notification' in window) {
        if (Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }

    // Chat functionality (placeholder)
    const chatToggle = document.querySelector('#chat-toggle');
    const chatWindow = document.querySelector('#chat-window');
    
    if (chatToggle && chatWindow) {
        chatToggle.addEventListener('click', function() {
            chatWindow.classList.toggle('d-none');
        });
    }

    // Geolocation for local guides
    const locationButton = document.querySelector('#get-location');
    if (locationButton) {
        locationButton.addEventListener('click', function() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        const lat = position.coords.latitude;
                        const lng = position.coords.longitude;
                        
                        // You would typically reverse geocode this to get city name
                        console.log('Current location:', lat, lng);
                        
                        // Show success message
                        this.innerHTML = '<i class="fas fa-check"></i> Location Detected';
                        this.classList.add('btn-success');
                    },
                    function(error) {
                        console.error('Error getting location:', error);
                        alert('Unable to get your location. Please enter manually.');
                    }
                );
            } else {
                alert('Geolocation is not supported by this browser.');
            }
        });
    }

    // Form auto-save (localStorage)
    const autoSaveForms = document.querySelectorAll('.auto-save');
    autoSaveForms.forEach(form => {
        const formId = form.id;
        
        // Load saved data
        const savedData = localStorage.getItem(`form_${formId}`);
        if (savedData) {
            const data = JSON.parse(savedData);
            Object.keys(data).forEach(key => {
                const input = form.querySelector(`[name="${key}"]`);
                if (input) {
                    input.value = data[key];
                }
            });
        }
        
        // Save data on input
        form.addEventListener('input', function(e) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
                const formData = new FormData(form);
                const data = {};
                for (let [key, value] of formData.entries()) {
                    data[key] = value;
                }
                localStorage.setItem(`form_${formId}`, JSON.stringify(data));
            }
        });
        
        // Clear saved data on successful submit
        form.addEventListener('submit', function() {
            localStorage.removeItem(`form_${formId}`);
        });
    });

    // Initialize any additional features
    initializeAdditionalFeatures();
});

function initializeAdditionalFeatures() {
    // Add any additional feature initialization here
    console.log('LocalLink app initialized successfully');
}

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    }).format(new Date(date));
}

function showNotification(title, message, type = 'info') {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, {
            body: message,
            icon: '/static/images/logo.png'
        });
    }
}

// Export functions for use in other scripts
window.LocalLink = {
    formatCurrency,
    formatDate,
    showNotification
};
