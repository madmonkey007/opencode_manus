// History Fix v2 - Enhanced with own event rendering
console.log('[History Fix v2] Loading...');

// Render timeline event directly to DOM
function renderTimelineEvent(step, index, total) {
    try {
        console.log(`[History Fix v2] Rendering event ${index + 1}/${total}:`, step);

        const action = step.action || step.action_type || 'unknown';
        const path = step.path || step.file_path || '';
        const toolName = step.tool_name || '';

        // Build title
        let title = `[${action}]`;
        if (toolName) title += ` ${toolName}`;
        if (path) title += ` ${path}`;

        // Build content
        let content = '';
        content += `Step ID: ${step.step_id || 'N/A'}\n`;
        content += `Action: ${action}\n`;
        if (toolName) content += `Tool: ${toolName}\n`;
        if (path) content += `Path: ${path}\n`;
        if (step.timestamp) content += `Time: ${step.timestamp}`;

        // Method 1: Try rightPanelManager
        if (window.rightPanelManager) {
            try {
                if (typeof window.rightPanelManager.show === 'function') {
                    window.rightPanelManager.show();
                }
                if (typeof window.rightPanelManager.switchTab === 'function') {
                    window.rightPanelManager.switchTab('preview');
                }
                if (typeof window.rightPanelManager.showFileEditor === 'function') {
                    window.rightPanelManager.showFileEditor(title, content);
                }
                console.log('[History Fix v2] ✓ Rendered to rightPanelManager');
            } catch (e) {
                console.log('[History Fix v2] rightPanelManager error:', e);
            }
        }

        // Method 2: Add to console area
        const consoleSelectors = [
            '[data-testid="console"]',
            '.console-output',
            '#console',
            '.console'
        ];

        let consoleDiv = null;
        for (const selector of consoleSelectors) {
            consoleDiv = document.querySelector(selector);
            if (consoleDiv) break;
        }

        if (consoleDiv) {
            const eventDiv = document.createElement('div');
            eventDiv.style.cssText = `
                padding: 10px;
                margin: 5px 0;
                background: #f5f5f5;
                border-left: 4px solid #333;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.5;
            `;

            // Format content
            const formattedContent = content.replace(/\n/g, '<br>');
            eventDiv.innerHTML = `<strong style="color: #333;">${title}</strong><br>${formattedContent}`;

            // Append to console
            consoleDiv.appendChild(eventDiv);
            consoleDiv.scrollTop = consoleDiv.scrollHeight;

            console.log('[History Fix v2] ✓ Rendered to console div');
        }

    } catch (error) {
        console.error('[History Fix v2] Error rendering event:', error);
    }
}

// Load timeline for a session
window.loadSessionTimeline = async function(sessionId) {
    try {
        console.log('[History Fix v2] Loading timeline for session:', sessionId);

        const response = await fetch(`/opencode/session/${sessionId}/timeline`);
        if (!response.ok) {
            console.error('[History Fix v2] Failed to load timeline:', response.status);
            return;
        }

        const data = await response.json();
        const timeline = data.timeline || [];

        console.log(`[History Fix v2] Timeline events count: ${timeline.length}`);

        if (timeline.length === 0) {
            console.log('[History Fix v2] No timeline events found');
            return;
        }

        // Render each timeline event
        timeline.forEach((step, index) => {
            console.log(`[History Fix v2] Processing event ${index + 1}/${timeline.length}`);
            renderTimelineEvent(step, index, timeline.length);
        });

        console.log('[History Fix v2] ✓ All timeline events rendered');

    } catch (error) {
        console.error('[History Fix v2] Error loading timeline:', error);
    }
};

// Handle history session click
window.handleHistorySessionClick = async function(sessionId) {
    console.log('[History Fix v2] Loading session:', sessionId);

    try {
        const response = await fetch(`/opencode/session/${sessionId}/messages`);
        if (!response.ok) {
            throw new Error(`Failed: ${response.status}`);
        }

        const data = await response.json();
        console.log('[History Fix v2] Messages loaded:', data.messages?.length || 0);

        // Load timeline
        await window.loadSessionTimeline(sessionId);

        console.log('[History Fix v2] Session loaded:', sessionId);

    } catch (error) {
        console.error('[History Fix v2] Error:', error);
    }
};

console.log('[History Fix v2] ✓ Global functions loaded');
console.log('[History Fix v2] typeof window.loadSessionTimeline:', typeof window.loadSessionTimeline);
