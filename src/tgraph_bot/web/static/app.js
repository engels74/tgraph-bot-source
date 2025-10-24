/**
 * TGraph Bot Web UI JavaScript
 *
 * This file provides client-side functionality for the configuration interface.
 * Requirements: 4.2, 4.3, 4.4, 4.5
 */

// Global state
let currentConfig = null;
let fileModifiedTimestamp = null;
let checkModificationInterval = null;

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
}

/**
 * Update the last modified display
 */
function updateLastModified() {
    const lastModifiedElement = document.getElementById('last-modified');
    if (lastModifiedElement) {
        const timestamp = parseFloat(lastModifiedElement.textContent);
        if (!isNaN(timestamp)) {
            lastModifiedElement.textContent = formatTimestamp(timestamp);
            fileModifiedTimestamp = timestamp;
        }
    }
}

/**
 * Show status message
 */
function showStatus(message, type = 'info') {
    const statusElement = document.getElementById('status-message');
    if (statusElement) {
        statusElement.textContent = message;
        statusElement.className = `status-message ${type}`;
        statusElement.classList.remove('hidden');

        // Auto-hide success messages after 5 seconds
        if (type === 'success') {
            setTimeout(() => {
                statusElement.classList.add('hidden');
            }, 5000);
        }
    }
}

/**
 * Hide status message
 */
function hideStatus() {
    const statusElement = document.getElementById('status-message');
    if (statusElement) {
        statusElement.classList.add('hidden');
    }
}

/**
 * Set nested object value using dot notation path
 */
function setNestedValue(obj, path, value) {
    const keys = path.split('.');
    let current = obj;

    for (let i = 0; i < keys.length - 1; i++) {
        const key = keys[i];
        if (!(key in current)) {
            current[key] = {};
        }
        current = current[key];
    }

    current[keys[keys.length - 1]] = value;
}

/**
 * Get nested object value using dot notation path
 */
function getNestedValue(obj, path) {
    const keys = path.split('.');
    let current = obj;

    for (const key of keys) {
        if (current === null || current === undefined) {
            return undefined;
        }
        current = current[key];
    }

    return current;
}

/**
 * Load configuration from API
 */
async function loadConfiguration() {
    try {
        showStatus('Loading configuration...', 'info');

        const response = await fetch('/api/config');
        if (!response.ok) {
            throw new Error(`Failed to load configuration: ${response.statusText}`);
        }

        const data = await response.json();
        currentConfig = data.config;
        fileModifiedTimestamp = data.file_modified;

        // Update UI
        populateForm(currentConfig);
        updateLastModifiedDisplay(fileModifiedTimestamp);

        hideStatus();
        return true;
    } catch (error) {
        showStatus(`Error loading configuration: ${error.message}`, 'error');
        console.error('Failed to load configuration:', error);
        return false;
    }
}

/**
 * Update last modified display
 */
function updateLastModifiedDisplay(timestamp) {
    const lastModifiedElement = document.getElementById('last-modified');
    if (lastModifiedElement) {
        lastModifiedElement.textContent = formatTimestamp(timestamp);
    }
}

/**
 * Populate form with configuration data
 */
function populateForm(config) {
    const form = document.getElementById('config-form');
    if (!form) return;

    // Iterate through all form inputs
    const inputs = form.querySelectorAll('input, select');
    inputs.forEach(input => {
        const name = input.getAttribute('name');
        if (!name) return;

        const value = getNestedValue(config, name);
        if (value === undefined) return;

        if (input.type === 'checkbox') {
            input.checked = Boolean(value);
        } else if (input.type === 'color') {
            // Ensure color value is in hex format
            input.value = value;
        } else if (input.type === 'number') {
            input.value = value;
        } else {
            input.value = value;
        }
    });
}

/**
 * Extract configuration from form
 */
function extractFormData() {
    const form = document.getElementById('config-form');
    if (!form) return null;

    const config = {};

    // Iterate through all form inputs
    const inputs = form.querySelectorAll('input, select');
    inputs.forEach(input => {
        const name = input.getAttribute('name');
        if (!name) return;

        let value;
        if (input.type === 'checkbox') {
            value = input.checked;
        } else if (input.type === 'number') {
            value = parseFloat(input.value);
        } else {
            value = input.value;
        }

        setNestedValue(config, name, value);
    });

    return config;
}

/**
 * Validate form
 */
function validateForm() {
    const form = document.getElementById('config-form');
    if (!form) return false;

    // Use HTML5 validation
    if (!form.checkValidity()) {
        form.reportValidity();
        return false;
    }

    return true;
}

/**
 * Save configuration
 */
async function saveConfiguration() {
    try {
        // Validate form
        if (!validateForm()) {
            showStatus('Please fix validation errors before saving', 'error');
            return false;
        }

        // Extract form data
        const config = extractFormData();
        if (!config) {
            showStatus('Failed to extract form data', 'error');
            return false;
        }

        // Show loading state
        const saveBtn = document.getElementById('save-btn');
        const originalText = saveBtn.textContent;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="loading"></span> Saving...';

        showStatus('Saving configuration...', 'info');

        // Send to API
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                config: config,
                file_modified: fileModifiedTimestamp
            })
        });

        const data = await response.json();

        // Restore button state
        saveBtn.disabled = false;
        saveBtn.textContent = originalText;

        if (!response.ok) {
            if (data.conflict) {
                showStatus('Configuration file was modified externally. Please reload.', 'warning');
                showExternalModificationWarning();
            } else {
                throw new Error(data.error || `Save failed: ${response.statusText}`);
            }
            return false;
        }

        showStatus('Configuration saved successfully!', 'success');

        // Reload configuration to get latest state
        await loadConfiguration();

        return true;
    } catch (error) {
        showStatus(`Error saving configuration: ${error.message}`, 'error');
        console.error('Failed to save configuration:', error);

        // Restore button state
        const saveBtn = document.getElementById('save-btn');
        saveBtn.disabled = false;
        saveBtn.textContent = '💾 Save Configuration';

        return false;
    }
}

/**
 * Reload configuration from file
 */
async function reloadConfiguration() {
    try {
        const reloadBtn = document.getElementById('reload-btn');
        const originalText = reloadBtn.textContent;
        reloadBtn.disabled = true;
        reloadBtn.innerHTML = '<span class="loading"></span> Reloading...';

        showStatus('Reloading configuration from file...', 'info');

        const response = await fetch('/api/config/reload', {
            method: 'POST'
        });

        const data = await response.json();

        // Restore button state
        reloadBtn.disabled = false;
        reloadBtn.textContent = originalText;

        if (!response.ok) {
            throw new Error(data.error || `Reload failed: ${response.statusText}`);
        }

        showStatus('Configuration reloaded successfully!', 'success');

        // Load fresh configuration
        await loadConfiguration();
        hideExternalModificationWarning();

        return true;
    } catch (error) {
        showStatus(`Error reloading configuration: ${error.message}`, 'error');
        console.error('Failed to reload configuration:', error);

        // Restore button state
        const reloadBtn = document.getElementById('reload-btn');
        reloadBtn.disabled = false;
        reloadBtn.textContent = '🔄 Reload from File';

        return false;
    }
}

/**
 * Check if file was modified externally
 */
async function checkFileModification() {
    try {
        if (!fileModifiedTimestamp) return;

        const response = await fetch(`/api/config/file-modified?timestamp=${fileModifiedTimestamp}`);
        if (!response.ok) return;

        const data = await response.json();

        if (data.modified) {
            showExternalModificationWarning();
            fileModifiedTimestamp = data.current_timestamp;
            updateLastModifiedDisplay(data.current_timestamp);
        }
    } catch (error) {
        console.error('Failed to check file modification:', error);
    }
}

/**
 * Show external modification warning
 */
function showExternalModificationWarning() {
    const warning = document.getElementById('external-modification-warning');
    if (warning) {
        warning.classList.remove('hidden');
    }
}

/**
 * Hide external modification warning
 */
function hideExternalModificationWarning() {
    const warning = document.getElementById('external-modification-warning');
    if (warning) {
        warning.classList.add('hidden');
    }
}

/**
 * Start periodic file modification check
 */
function startFileModificationCheck() {
    // Check every 5 seconds
    checkModificationInterval = setInterval(checkFileModification, 5000);
}

/**
 * Stop periodic file modification check
 */
function stopFileModificationCheck() {
    if (checkModificationInterval) {
        clearInterval(checkModificationInterval);
        checkModificationInterval = null;
    }
}

/**
 * Toggle sensitive value visibility
 */
function toggleSensitiveValue(button) {
    const targetId = button.getAttribute('data-target');
    const input = document.getElementById(targetId);

    if (!input) return;

    if (input.type === 'password') {
        input.type = 'text';
        button.textContent = '🙈 Hide';
    } else {
        input.type = 'password';
        button.textContent = '👁️ Show';
    }
}

/**
 * Handle form submission
 */
async function handleFormSubmit(event) {
    event.preventDefault();
    await saveConfiguration();
}

/**
 * Initialize event listeners
 */
function initializeEventListeners() {
    // Form submission
    const form = document.getElementById('config-form');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }

    // Reload button
    const reloadBtn = document.getElementById('reload-btn');
    if (reloadBtn) {
        reloadBtn.addEventListener('click', reloadConfiguration);
    }

    // Toggle visibility buttons for sensitive inputs
    const toggleButtons = document.querySelectorAll('.toggle-visibility');
    toggleButtons.forEach(button => {
        button.addEventListener('click', () => toggleSensitiveValue(button));
    });

    // Real-time validation feedback
    const inputs = document.querySelectorAll('input, select');
    inputs.forEach(input => {
        input.addEventListener('blur', () => {
            if (input.validity.valid) {
                input.classList.remove('invalid');
            } else {
                input.classList.add('invalid');
            }
        });
    });
}

/**
 * Initialize the application
 */
async function initialize() {
    console.log('TGraph Bot Web UI initializing...');

    // Update last modified display
    updateLastModified();

    // Initialize event listeners
    initializeEventListeners();

    // Load configuration
    const success = await loadConfiguration();

    if (success) {
        // Start periodic file modification check
        startFileModificationCheck();
        console.log('TGraph Bot Web UI initialized successfully');
    } else {
        console.error('Failed to initialize TGraph Bot Web UI');
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initialize);

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    stopFileModificationCheck();
});

