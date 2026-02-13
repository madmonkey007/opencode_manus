/**
 * Timeline Progress - 时间轴进度条组件
 * 显示任务执行的时间轴和进度
 */

class TimelineProgress {
    constructor(containerSelector) {
        this.container = document.querySelector(containerSelector);
        this.timeline = [];
        this.activeStepId = null;
        this.stepClickCallback = null;

        if (this.container) {
            this.init();
        }
    }

    init() {
        this.render();
    }

    setTimeline(timeline) {
        // 设置时间轴数据
        this.timeline = timeline || [];
        this.render();
    }

    addStep(step) {
        // 添加单个步骤到时间轴
        this.timeline.push(step);
        this.render();
    }

    setActiveStep(stepId) {
        // 设置当前活动步骤
        this.activeStepId = stepId;
        this.render();
    }

    render() {
        if (!this.container) return;

        const totalSteps = this.timeline.length;
        const activeIndex = this.timeline.findIndex(s => s.step_id === this.activeStepId);
        const progress = totalSteps > 0 ? ((activeIndex + 1) / totalSteps) * 100 : 0;

        this.container.innerHTML = `
            <!-- 进度条 -->
            <div class="w-full bg-gray-200 dark:bg-zinc-700 rounded-full h-2 mb-3 overflow-hidden">
                <div class="bg-blue-500 h-2 transition-all duration-300" style="width: ${progress}%"></div>
            </div>

            <!-- 时间轴节点 -->
            <div class="flex items-center gap-1 overflow-x-auto pb-2 scrollbar-hide">
                ${this.timeline.map((step, index) => this.renderStepNode(step, index)).join('')}
            </div>

            <!-- 当前步骤信息 -->
            ${this.activeStepId ? this.renderCurrentStepInfo() : ''}
        `;

        // 绑定点击事件
        this.container.querySelectorAll('.timeline-step-node').forEach(node => {
            node.onclick = () => {
                const stepId = node.dataset.stepId;
                if (this.stepClickCallback) {
                    this.stepClickCallback(stepId);
                }
            };
        });
    }

    renderStepNode(step, index) {
        const isActive = step.step_id === this.activeStepId;
        const isCompleted = this.activeStepId && index < this.timeline.findIndex(s => s.step_id === this.activeStepId);

        const actionIcons = {
            'write': 'edit_note',
            'edit': 'edit',
            'bash': 'terminal',
            'read': 'visibility',
            'grep': 'search'
        };

        const icon = actionIcons[step.action] || 'description';

        return `
            <div class="timeline-step-node flex-shrink-0 cursor-pointer group relative" data-step-id="${step.step_id}">
                <!-- 节点图标 -->
                <div class="w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200 ${
                    isActive ? 'bg-blue-500 text-white scale-110' :
                    isCompleted ? 'bg-green-500 text-white' :
                    'bg-gray-300 dark:bg-zinc-600 text-gray-600 dark:text-gray-400'
                } group-hover:scale-110">
                    <span class="material-symbols-outlined text-[16px]">${icon}</span>
                </div>

                <!-- 工具提示 -->
                <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10">
                    <div class="bg-gray-900 dark:bg-zinc-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap shadow-lg">
                        ${this.formatStepTooltip(step)}
                    </div>
                </div>
            </div>
        `;
    }

    renderCurrentStepInfo() {
        const currentStep = this.timeline.find(s => s.step_id === this.activeStepId);
        if (!currentStep) return '';

        return `
            <div class="mt-3 text-xs text-gray-600 dark:text-gray-400 border-t border-gray-200 dark:border-zinc-700 pt-2">
                <span class="font-medium">${currentStep.brief || currentStep.action}</span>
                ${currentStep.path ? `<span class="ml-2 text-gray-500">${currentStep.path.split('/').pop()}</span>` : ''}
            </div>
        `;
    }

    formatStepTooltip(step) {
        const actionLabels = {
            'write': '写入',
            'edit': '编辑',
            'bash': '执行',
            'read': '读取',
            'grep': '搜索'
        };

        const label = actionLabels[step.action] || step.action;
        const filename = step.path ? step.path.split('/').pop() : '';
        const time = step.timestamp ? new Date(step.timestamp).toLocaleTimeString() : '';

        return `${label} ${filename}${time ? ' · ' + time : ''}`;
    }

    onStepClick(callback) {
        // 设置节点点击回调
        this.stepClickCallback = callback;
    }

    setOnStepClick(callback) {
        // 设置节点点击回调（别名方法）
        this.stepClickCallback = callback;
    }

    clear() {
        // 清空时间轴
        this.timeline = [];
        this.activeStepId = null;
        this.render();
    }

    destroy() {
        // 清理组件
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// 初始化并导出
let timelineProgress;

function initTimelineProgress(containerSelector) {
    timelineProgress = new TimelineProgress(containerSelector);
    window.timelineProgress = timelineProgress;
    return timelineProgress;
}

// 导出初始化函数
window.initTimelineProgress = initTimelineProgress;
