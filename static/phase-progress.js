/**
 * Phase Progress Component
 * Displays multi-phase task execution progress with visual indicators
 */

class PhaseProgress {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.phases = [];
        this.currentPhaseId = null;
        this.goal = "";
    }

    /**
     * Initialize or update the phase progress display
     * @param {Object} plan - Plan object with goal, phases, and current_phase_id
     */
    update(plan) {
        this.goal = plan.goal;
        this.phases = plan.phases;
        this.currentPhaseId = plan.current_phase_id;
        this.render();
    }

    /**
     * Render the phase progress UI
     */
    render() {
        if (!this.container) return;

        // Clear container
        this.container.innerHTML = '';

        // Create goal header
        const goalHeader = document.createElement('div');
        goalHeader.className = 'phase-goal p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg mb-3';
        goalHeader.innerHTML = `
            <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-blue-600 dark:text-blue-400">flag</span>
                <div class="flex-1">
                    <div class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Task Goal</div>
                    <div class="text-sm font-medium text-gray-800 dark:text-gray-200">${this.escapeHtml(this.goal)}</div>
                </div>
            </div>
        `;
        this.container.appendChild(goalHeader);

        // Create phases container
        const phasesContainer = document.createElement('div');
        phasesContainer.className = 'phases-list space-y-2';

        this.phases.forEach((phase, index) => {
            const phaseEl = this.createPhaseElement(phase, index);
            phasesContainer.appendChild(phaseEl);
        });

        this.container.appendChild(phasesContainer);

        // Add progress bar
        const progressBar = this.createProgressBar();
        this.container.appendChild(progressBar);
    }

    /**
     * Create a single phase element
     * @param {Object} phase - Phase object
     * @param {number} index - Phase index
     * @returns {HTMLElement}
     */
    createPhaseElement(phase, index) {
        const isActive = phase.id === this.currentPhaseId;
        const isCompleted = phase.status === 'completed';
        const isPending = phase.status === 'pending';
        const isFailed = phase.status === 'failed';

        const phaseEl = document.createElement('div');
        phaseEl.className = `phase-item p-3 rounded-lg border-2 transition-all ${this.getPhaseClasses(phase)}`;
        phaseEl.dataset.phaseId = phase.id;

        // Status icon
        let statusIcon = '';
        if (isCompleted) {
            statusIcon = '<span class="material-symbols-outlined text-green-600">check_circle</span>';
        } else if (isActive) {
            statusIcon = '<span class="material-symbols-outlined text-blue-600 animate-spin">sync</span>';
        } else if (isFailed) {
            statusIcon = '<span class="material-symbols-outlined text-red-600">error</span>';
        } else {
            statusIcon = '<span class="material-symbols-outlined text-gray-400">radio_button_unchecked</span>';
        }

        phaseEl.innerHTML = `
            <div class="flex items-start gap-3">
                <div class="phase-icon mt-0.5">${statusIcon}</div>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                        <span class="phase-number text-xs font-bold ${this.getPhaseNumberColor(phase)}">
                            Phase ${phase.phase_number}
                        </span>
                        <span class="phase-status text-xs px-2 py-0.5 rounded-full ${this.getStatusBadgeClass(phase)}">
                            ${this.getStatusText(phase)}
                        </span>
                    </div>
                    <div class="phase-title text-sm font-medium text-gray-800 dark:text-gray-200 mb-1">
                        ${this.escapeHtml(phase.title)}
                    </div>
                    ${this.renderCapabilities(phase.capabilities)}
                    ${this.renderTimestamps(phase)}
                </div>
            </div>
        `;

        // Add click handler for expandable details
        phaseEl.style.cursor = 'pointer';
        phaseEl.addEventListener('click', () => this.togglePhaseDetails(phase.id));

        return phaseEl;
    }

    /**
     * Get CSS classes for phase item based on status
     */
    getPhaseClasses(phase) {
        const isActive = phase.id === this.currentPhaseId;
        const isCompleted = phase.status === 'completed';
        const isFailed = phase.status === 'failed';

        if (isActive) {
            return 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 shadow-sm';
        } else if (isCompleted) {
            return 'border-green-500 bg-green-50 dark:bg-green-900/20';
        } else if (isFailed) {
            return 'border-red-500 bg-red-50 dark:bg-red-900/20';
        } else {
            return 'border-gray-300 dark:border-gray-700 bg-white dark:bg-zinc-800';
        }
    }

    /**
     * Get color class for phase number
     */
    getPhaseNumberColor(phase) {
        const isActive = phase.id === this.currentPhaseId;
        const isCompleted = phase.status === 'completed';

        if (isActive) return 'text-blue-600 dark:text-blue-400';
        if (isCompleted) return 'text-green-600 dark:text-green-400';
        return 'text-gray-500 dark:text-gray-400';
    }

    /**
     * Get status badge CSS classes
     */
    getStatusBadgeClass(phase) {
        switch (phase.status) {
            case 'active':
                return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300';
            case 'completed':
                return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
            case 'failed':
                return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300';
            default:
                return 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300';
        }
    }

    /**
     * Get human-readable status text
     */
    getStatusText(phase) {
        switch (phase.status) {
            case 'active': return '⟳ In Progress';
            case 'completed': return '✓ Completed';
            case 'failed': return '✗ Failed';
            default: return '○ Pending';
        }
    }

    /**
     * Render capabilities badges
     */
    renderCapabilities(capabilities) {
        if (!capabilities || Object.keys(capabilities).length === 0) {
            return '';
        }

        const activeCapabilities = Object.entries(capabilities)
            .filter(([_, enabled]) => enabled)
            .map(([name, _]) => name);

        if (activeCapabilities.length === 0) return '';

        const badges = activeCapabilities.map(cap => {
            const icon = this.getCapabilityIcon(cap);
            return `<span class="capability-badge inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                <span class="material-symbols-outlined text-sm">${icon}</span>
                ${this.formatCapabilityName(cap)}
            </span>`;
        }).join('');

        return `<div class="capabilities flex flex-wrap gap-1 mt-2">${badges}</div>`;
    }

    /**
     * Get icon for capability
     */
    getCapabilityIcon(capability) {
        const icons = {
            'creative_writing': 'edit_note',
            'data_analysis': 'analytics',
            'deep_research': 'search',
            'image_processing': 'image',
            'media_generation': 'auto_awesome',
            'parallel_processing': 'account_tree',
            'slides_content_writing': 'article',
            'slides_generation': 'slideshow',
            'technical_writing': 'code',
            'web_development': 'web'
        };
        return icons[capability] || 'extension';
    }

    /**
     * Format capability name for display
     */
    formatCapabilityName(name) {
        return name.split('_').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    }

    /**
     * Render timestamps
     */
    renderTimestamps(phase) {
        if (!phase.started_at && !phase.completed_at) return '';

        let html = '<div class="timestamps text-xs text-gray-500 dark:text-gray-400 mt-2 space-y-0.5">';
        
        if (phase.started_at) {
            html += `<div>Started: ${this.formatTimestamp(phase.started_at)}</div>`;
        }
        if (phase.completed_at) {
            html += `<div>Completed: ${this.formatTimestamp(phase.completed_at)}</div>`;
        }
        
        html += '</div>';
        return html;
    }

    /**
     * Format timestamp for display
     */
    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    /**
     * Create progress bar showing overall completion
     */
    createProgressBar() {
        const completedCount = this.phases.filter(p => p.status === 'completed').length;
        const totalCount = this.phases.length;
        const percentage = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar-container mt-4 p-3 bg-gray-50 dark:bg-zinc-900 rounded-lg';
        progressBar.innerHTML = `
            <div class="flex justify-between items-center mb-2">
                <span class="text-xs font-medium text-gray-600 dark:text-gray-400">Overall Progress</span>
                <span class="text-xs font-bold text-blue-600 dark:text-blue-400">${completedCount}/${totalCount} phases</span>
            </div>
            <div class="progress-bar w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div class="progress-fill h-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-500" 
                     style="width: ${percentage}%"></div>
            </div>
        `;

        return progressBar;
    }

    /**
     * Toggle phase details (for future expansion)
     */
    togglePhaseDetails(phaseId) {
        // Placeholder for expandable phase details
        console.log('Phase clicked:', phaseId);
        // Could show logs, tool calls, etc. for this phase
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Clear the display
     */
    clear() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export for use in main app
window.PhaseProgress = PhaseProgress;
