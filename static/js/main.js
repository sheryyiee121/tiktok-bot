// Main JavaScript for TikTok DM Bot

document.addEventListener('DOMContentLoaded', function () {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize the app
    initializeApp();

    // Start periodic updates
    startPeriodicUpdates();

    // Add fade-in animation to cards
    addFadeInAnimation();
});

function initializeApp() {
    console.log('TikTok DM Bot initialized');

    // Add event listeners
    addEventListeners();

    // Check bot status on load
    updateBotStatus();

    // Update timestamp displays
    updateTimestamps();
}

function addEventListeners() {
    // Add click handlers for quick actions
    const quickActionBtns = document.querySelectorAll('.btn[data-action]');
    quickActionBtns.forEach(btn => {
        btn.addEventListener('click', handleQuickAction);
    });

    // Add form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', validateForm);
    });

    // Add auto-save for settings
    const settingsInputs = document.querySelectorAll('#advancedSettingsForm input, #advancedSettingsForm textarea');
    settingsInputs.forEach(input => {
        input.addEventListener('change', autoSaveSettings);
    });
}

function handleQuickAction(event) {
    const action = event.target.getAttribute('data-action');

    switch (action) {
        case 'refresh':
            refreshData();
            break;
        case 'clear-messages':
            clearMessages();
            break;
        case 'export-logs':
            exportLogs();
            break;
        default:
            console.log('Unknown action:', action);
    }
}

function validateForm(event) {
    const form = event.target;
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });

    if (!isValid) {
        event.preventDefault();
        showNotification('Please fill in all required fields', 'error');
    }
}

function autoSaveSettings() {
    // Debounce auto-save
    clearTimeout(window.autoSaveTimeout);
    window.autoSaveTimeout = setTimeout(() => {
        const formData = new FormData(document.getElementById('advancedSettingsForm'));

        // Show saving indicator
        showNotification('Settings auto-saved', 'success', 2000);

        // In a real app, this would send the data to the server
        console.log('Auto-saving settings:', Object.fromEntries(formData));
    }, 1000);
}

function startPeriodicUpdates() {
    // Update bot status every 30 seconds
    setInterval(updateBotStatus, 30000);

    // Update message count every 10 seconds
    setInterval(updateMessageCount, 10000);

    // Update timestamps every minute
    setInterval(updateTimestamps, 60000);
}

function updateBotStatus() {
    fetch('/api/bot_status')
        .then(response => response.json())
        .then(data => {
            const statusElement = document.getElementById('bot-status');
            const statusIndicators = document.querySelectorAll('.status-indicator');

            if (statusElement) {
                if (data.active) {
                    statusElement.innerHTML = '<i class="fas fa-circle me-1"></i>Online';
                    statusElement.className = 'badge bg-success';
                } else {
                    statusElement.innerHTML = '<i class="fas fa-circle me-1"></i>Offline';
                    statusElement.className = 'badge bg-secondary';
                }
            }

            // Update status indicators
            statusIndicators.forEach(indicator => {
                if (data.active) {
                    indicator.classList.remove('bg-secondary');
                    indicator.classList.add('bg-success');
                } else {
                    indicator.classList.remove('bg-success');
                    indicator.classList.add('bg-secondary');
                }
            });
        })
        .catch(error => {
            console.error('Error updating bot status:', error);
        });
}

function updateMessageCount() {
    fetch('/api/messages')
        .then(response => response.json())
        .then(data => {
            const countElements = document.querySelectorAll('[data-message-count]');
            countElements.forEach(element => {
                element.textContent = data.length;
            });
        })
        .catch(error => {
            console.error('Error updating message count:', error);
        });
}

function updateTimestamps() {
    const timestamps = document.querySelectorAll('[data-timestamp]');
    const now = new Date();

    timestamps.forEach(element => {
        const timestamp = new Date(element.getAttribute('data-timestamp'));
        const diff = now - timestamp;
        element.textContent = formatTimeDiff(diff);
    });
}

function formatTimeDiff(diff) {
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'Just now';
}

function refreshData() {
    // Show loading state
    const refreshBtn = document.querySelector('[onclick="refreshData()"]');
    if (refreshBtn) {
        const originalHTML = refreshBtn.innerHTML;
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Refreshing...';
        refreshBtn.disabled = true;

        // Simulate refresh delay
        setTimeout(() => {
            refreshBtn.innerHTML = originalHTML;
            refreshBtn.disabled = false;
            location.reload();
        }, 1000);
    }
}

function clearMessages() {
    if (confirm('Are you sure you want to clear all messages? This action cannot be undone.')) {
        // In a real app, this would make an API call
        showNotification('Messages cleared successfully', 'success');

        // Remove message items from UI
        const messageItems = document.querySelectorAll('.message-item');
        messageItems.forEach(item => {
            item.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => item.remove(), 300);
        });
    }
}

function exportLogs() {
    // Create sample log data
    const logs = [
        { timestamp: new Date().toISOString(), level: 'INFO', message: 'Bot started' },
        { timestamp: new Date().toISOString(), level: 'INFO', message: 'Message sent to user123' },
        { timestamp: new Date().toISOString(), level: 'SUCCESS', message: 'Auto-response triggered' }
    ];

    const logData = logs.map(log =>
        `[${log.timestamp}] ${log.level}: ${log.message}`
    ).join('\n');

    const blob = new Blob([logData], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `tiktok-bot-logs-${new Date().toISOString().split('T')[0]}.txt`;
    a.click();

    URL.revokeObjectURL(url);
    showNotification('Logs exported successfully', 'success');
}

function showNotification(message, type = 'info', duration = 3000) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';

    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 150);
        }
    }, duration);
}

function addFadeInAnimation() {
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';

        setTimeout(() => {
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

// Utility functions
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Copied to clipboard', 'success', 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        showNotification('Failed to copy to clipboard', 'error');
    });
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Real-time features
function startWebSocketConnection() {
    // In a real app, this would establish a WebSocket connection
    // for real-time updates
    console.log('WebSocket connection would be established here');
}

// Keyboard shortcuts
document.addEventListener('keydown', function (event) {
    // Ctrl/Cmd + R: Refresh data
    if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
        event.preventDefault();
        refreshData();
    }

    // Ctrl/Cmd + S: Save settings (on settings page)
    if ((event.ctrlKey || event.metaKey) && event.key === 's') {
        const saveBtn = document.querySelector('[onclick="saveAllSettings()"]');
        if (saveBtn) {
            event.preventDefault();
            saveAllSettings();
        }
    }
});

// Simulation state management
window.SimulationState = {
    isConnected: false,
    isDMActive: false,
    dmCounter: 0,
    dmInterval: null,

    setConnected: function (connected) {
        this.isConnected = connected;
        this.updateGlobalState();
    },

    setDMActive: function (active) {
        this.isDMActive = active;
        this.updateGlobalState();
    },

    incrementDMCounter: function () {
        this.dmCounter++;
        this.updateGlobalState();
    },

    updateGlobalState: function () {
        // Update any global UI elements that need to reflect simulation state
        const event = new CustomEvent('simulationStateChanged', {
            detail: {
                isConnected: this.isConnected,
                isDMActive: this.isDMActive,
                dmCounter: this.dmCounter
            }
        });
        document.dispatchEvent(event);
    }
};

// Listen for simulation state changes
document.addEventListener('simulationStateChanged', function (event) {
    const { isConnected, isDMActive, dmCounter } = event.detail;

    // Update navbar indicators if they exist
    const connectIndicator = document.querySelector('#navConnectIndicator');
    if (connectIndicator) {
        if (isConnected) {
            connectIndicator.innerHTML = '<i class="fas fa-circle text-success me-1"></i>Connected';
            connectIndicator.className = 'text-success small';
        } else {
            connectIndicator.innerHTML = '<i class="fas fa-circle text-secondary me-1"></i>Disconnected';
            connectIndicator.className = 'text-secondary small';
        }
    }

    // Update DM counters across pages
    const dmCounters = document.querySelectorAll('.dm-counter-global');
    dmCounters.forEach(counter => {
        counter.textContent = dmCounter;
    });

    // Update connection status indicator on dashboard
    const connectionStatusIndicator = document.getElementById('connectionStatusIndicator');
    if (connectionStatusIndicator) {
        if (isConnected) {
            connectionStatusIndicator.innerHTML = '<i class="fas fa-circle text-success me-1"></i>Account connected (demo_user_2024)';
        } else {
            connectionStatusIndicator.innerHTML = '<i class="fas fa-circle text-secondary me-1"></i>No account connected';
        }
    }
});

// Enhanced notification system with better animations
function showEnhancedNotification(message, type = 'info', duration = 3000, includeProgress = false) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px; animation: slideInRight 0.3s ease;';

    let progressBar = '';
    if (includeProgress) {
        progressBar = `<div class="progress mt-2" style="height: 3px;">
                        <div class="progress-bar progress-bar-animated" style="width: 100%; transition: width ${duration}ms linear;"></div>
                       </div>`;
    }

    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas ${getIconForType(type)} me-2"></i>
            <div class="flex-grow-1">${message}</div>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        ${progressBar}
    `;

    document.body.appendChild(notification);

    // Animate progress bar if included
    if (includeProgress) {
        setTimeout(() => {
            const progressBarEl = notification.querySelector('.progress-bar');
            if (progressBarEl) {
                progressBarEl.style.width = '0%';
            }
        }, 100);
    }

    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }
    }, duration);
}

function getIconForType(type) {
    const icons = {
        'success': 'fa-check-circle',
        'danger': 'fa-exclamation-triangle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle',
        'primary': 'fa-bell'
    };
    return icons[type] || icons['info'];
}

// Add CSS animations
const animationCSS = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .simulation-glow {
        animation: simulationGlow 2s infinite alternate;
    }
    
    @keyframes simulationGlow {
        from {
            box-shadow: 0 0 10px rgba(40, 167, 69, 0.5);
        }
        to {
            box-shadow: 0 0 20px rgba(40, 167, 69, 0.8);
        }
    }
`;

// Inject animation CSS
const style = document.createElement('style');
style.textContent = animationCSS;
document.head.appendChild(style);

// Export functions for global access
window.TikTokBot = {
    refreshData,
    clearMessages,
    exportLogs,
    showNotification,
    showEnhancedNotification,
    copyToClipboard,
    updateBotStatus,
    formatBytes,
    debounce,
    SimulationState: window.SimulationState
};
