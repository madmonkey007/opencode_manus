/**
 * Tool Visualizer Component
 * Displays tool calls with parameters, status, and results
 */

class ToolVisualizer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.toolCalls = [];
    }

    /**
     * Add a new tool call to the visualization
     * @param {Object} toolCall - Tool call object
     */
    addToolCall(toolCall) {
        this.toolCalls.push({
            id: toolCall.id || Date.now(),
            tool: toolCall.tool,
            status: toolCall.status || 'running',
            params: toolCall.params || {},
            result: toolCall.result || null,
            error: toolCall.error || null,
            timestamp: toolCall.timestamp || new Date().toISOString(),
            duration: toolCall.duration || null
        });
        this.render();
    }

    /**
     * Update an existing tool call
     * @param {string|number} id - Tool call ID
     * @param {Object} updates - Updates to apply
     */
    updateToolCall(id, updates) {
        const index = this.toolCalls.findIndex(tc => tc.id === id);
        if (index !== -1) {
            this.toolCalls[index] = { ...this.toolCalls[index], ...updates };
            this.render();
        }
    }

    /**
     * Render all tool calls
     */
    render() {
        if (!this.container) return;

        this.container.innerHTML = '';

        if (this.toolCalls.length === 0) {
            this.container.innerHTML = `
                <div class="empty-state text-center py-8 text-gray-400">
                    <span class="material-symbols-outlined text-4xl mb-2">build</span>
                    <p class="text-sm">No tools called yet</p>
                </div>
            `;
            return;
        }

        this.toolCalls.forEach(toolCall => {
            const toolEl = this.createToolElement(toolCall);
            this.container.appendChild(toolEl);
        });
    }

    /**
     * Create a tool call element
     * @param {Object} toolCall - Tool call data
     * @returns {HTMLElement}
     */
    createToolElement(toolCall) {
        const toolEl = document.createElement('div');
        toolEl.className = `tool-card mb-3 p-4 rounded-lg border-2 transition-all ${this.getToolCardClass(toolCall)}`;
        toolEl.dataset.toolId = toolCall.id;

        const icon = this.getToolIcon(toolCall.tool);
        const statusBadge = this.getStatusBadge(toolCall.status);

        toolEl.innerHTML = `
            <div class="tool-header flex items-start gap-3 mb-3">
                <div class="tool-icon w-10 h-10 rounded-lg ${this.getIconBgClass(toolCall.tool)} flex items-center justify-center">
                    <span class="material-symbols-outlined text-xl ${this.getIconColorClass(toolCall.tool)}">${icon}</span>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                        <h4 class="tool-name text-sm font-bold text-gray-800 dark:text-gray-200">${this.formatToolName(toolCall.tool)}</h4>
                        ${statusBadge}
                    </div>
                    <div class="tool-timestamp text-xs text-gray-500 dark:text-gray-400">
                        ${this.formatTimestamp(toolCall.timestamp)}
                        ${toolCall.duration ? ` • ${toolCall.duration}ms` : ''}
                    </div>
                </div>
                <button class="toggle-details text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors" 
                        onclick="window.toolVisualizer.toggleDetails('${toolCall.id}')">
                    <span class="material-symbols-outlined">expand_more</span>
                </button>
            </div>

            <div class="tool-details hidden" id="tool-details-${toolCall.id}">
                ${this.renderParameters(toolCall.params)}
                ${this.renderResult(toolCall)}
            </div>
        `;

        return toolEl;
    }

    /**
     * Get CSS class for tool card based on status
     */
    getToolCardClass(toolCall) {
        switch (toolCall.status) {
            case 'running':
                return 'border-blue-500 bg-blue-50 dark:bg-blue-900/20';
            case 'success':
                return 'border-green-500 bg-green-50 dark:bg-green-900/20';
            case 'error':
                return 'border-red-500 bg-red-50 dark:bg-red-900/20';
            default:
                return 'border-gray-300 dark:border-gray-700 bg-white dark:bg-zinc-800';
        }
    }

    /**
     * Get icon for tool
     */
    getToolIcon(toolName) {
        const icons = {
            'search': 'search',
            'browser': 'language',
            'file': 'description',
            'shell': 'terminal',
            'generate': 'auto_awesome',
            'webdev': 'code',
            'map': 'account_tree',
            'schedule': 'schedule',
            'message': 'chat'
        };
        return icons[toolName] || 'extension';
    }

    /**
     * Get icon background class
     */
    getIconBgClass(toolName) {
        const classes = {
            'search': 'bg-blue-100 dark:bg-blue-900/30',
            'browser': 'bg-purple-100 dark:bg-purple-900/30',
            'file': 'bg-green-100 dark:bg-green-900/30',
            'shell': 'bg-gray-100 dark:bg-gray-700',
            'generate': 'bg-pink-100 dark:bg-pink-900/30',
            'webdev': 'bg-orange-100 dark:bg-orange-900/30',
            'map': 'bg-indigo-100 dark:bg-indigo-900/30'
        };
        return classes[toolName] || 'bg-gray-100 dark:bg-gray-700';
    }

    /**
     * Get icon color class
     */
    getIconColorClass(toolName) {
        const classes = {
            'search': 'text-blue-600 dark:text-blue-400',
            'browser': 'text-purple-600 dark:text-purple-400',
            'file': 'text-green-600 dark:text-green-400',
            'shell': 'text-gray-600 dark:text-gray-400',
            'generate': 'text-pink-600 dark:text-pink-400',
            'webdev': 'text-orange-600 dark:text-orange-400',
            'map': 'text-indigo-600 dark:text-indigo-400'
        };
        return classes[toolName] || 'text-gray-600 dark:text-gray-400';
    }

    /**
     * Get status badge HTML
     */
    getStatusBadge(status) {
        const badges = {
            'running': '<span class="status-badge px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">⟳ Running</span>',
            'success': '<span class="status-badge px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300">✓ Success</span>',
            'error': '<span class="status-badge px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300">✗ Error</span>'
        };
        return badges[status] || '';
    }

    /**
     * Format tool name for display
     */
    formatToolName(name) {
        return name.split('_').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    }

    /**
     * Format timestamp
     */
    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    /**
     * Render parameters section
     */
    renderParameters(params) {
        if (!params || Object.keys(params).length === 0) {
            return '';
        }

        const paramsList = Object.entries(params).map(([key, value]) => {
            const displayValue = typeof value === 'object' 
                ? JSON.stringify(value, null, 2)
                : String(value);
            
            return `
                <div class="param-item mb-2">
                    <span class="param-key text-xs font-medium text-gray-600 dark:text-gray-400">${key}:</span>
                    <span class="param-value text-xs text-gray-800 dark:text-gray-200 ml-2">${this.escapeHtml(displayValue)}</span>
                </div>
            `;
        }).join('');

        return `
            <div class="parameters mb-3 p-3 bg-gray-50 dark:bg-zinc-900 rounded">
                <div class="text-xs font-bold text-gray-700 dark:text-gray-300 mb-2">Parameters</div>
                ${paramsList}
            </div>
        `;
    }

    /**
     * Render result section
     */
    renderResult(toolCall) {
        if (toolCall.status === 'running') {
            return '<div class="result text-xs text-gray-500 italic">Waiting for result...</div>';
        }

        if (toolCall.error) {
            return `
                <div class="error p-3 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800">
                    <div class="text-xs font-bold text-red-700 dark:text-red-300 mb-1">Error</div>
                    <div class="text-xs text-red-600 dark:text-red-400">${this.escapeHtml(toolCall.error)}</div>
                </div>
            `;
        }

        if (toolCall.result) {
            const resultDisplay = typeof toolCall.result === 'object'
                ? `<pre class="text-xs overflow-x-auto">${JSON.stringify(toolCall.result, null, 2)}</pre>`
                : `<div class="text-xs">${this.escapeHtml(String(toolCall.result))}</div>`;

            return `
                <div class="result p-3 bg-green-50 dark:bg-green-900/20 rounded border border-green-200 dark:border-green-800">
                    <div class="text-xs font-bold text-green-700 dark:text-green-300 mb-1">Result</div>
                    <div class="text-green-600 dark:text-green-400">${resultDisplay}</div>
                </div>
            `;
        }

        return '';
    }

    /**
     * Toggle details visibility
     */
    toggleDetails(toolId) {
        const detailsEl = document.getElementById(`tool-details-${toolId}`);
        if (detailsEl) {
            detailsEl.classList.toggle('hidden');
            
            // Rotate the expand icon
            const toolCard = document.querySelector(`[data-tool-id="${toolId}"]`);
            const expandIcon = toolCard.querySelector('.toggle-details span');
            if (expandIcon) {
                expandIcon.style.transform = detailsEl.classList.contains('hidden') 
                    ? 'rotate(0deg)' 
                    : 'rotate(180deg)';
            }
        }
    }

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Clear all tool calls
     */
    clear() {
        this.toolCalls = [];
        this.render();
    }
}

// Export for use in main app
window.ToolVisualizer = ToolVisualizer;
