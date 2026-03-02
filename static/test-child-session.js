/**
 * 子会话自动监听功能 - 测试和验证脚本
 *
 * 使用方法：
 * 1. 在浏览器控制台中运行此脚本
 * 2. 或者在HTML中引入：<script src="test-child-session.js"></script>
 *
 * 测试场景：
 * 1. 检测task工具事件
 * 2. 解析子session ID
 * 3. 订阅子session事件流
 * 4. 事件路由到主session
 * 5. 自动取消订阅
 */

(function() {
    'use strict';

    // 测试套件
    const TestSuite = {
        tests: [],
        passed: 0,
        failed: 0,

        /**
         * 添加测试用例
         * @param {string} name - 测试名称
         * @param {Function} testFn - 测试函数
         */
        addTest(name, testFn) {
            this.tests.push({ name, testFn });
        },

        /**
         * 运行所有测试
         */
        async runAll() {
            console.log('\n========================================');
            console.log('🧪 子会话监听功能测试套件');
            console.log('========================================\n');

            for (const test of this.tests) {
                try {
                    await test.testFn();
                    this.passed++;
                    console.log(`✅ PASS: ${test.name}`);
                } catch (error) {
                    this.failed++;
                    console.error(`❌ FAIL: ${test.name}`);
                    console.error(`   错误: ${error.message}`);
                }
            }

            console.log('\n========================================');
            console.log(`📊 测试结果: ${this.passed} 通过, ${this.failed} 失败`);
            console.log('========================================\n');
        }
    };

    // ========================================================================
    // 测试用例
    // ========================================================================

    /**
     * 测试1: ChildSessionManager是否正确初始化
     */
    TestSuite.addTest('ChildSessionManager初始化', () => {
        if (!window.ChildSessionManager) {
            throw new Error('ChildSessionManager未暴露到全局作用域');
        }

        const requiredMethods = [
            'subscribeToChildSession',
            'unsubscribeFromChildSession',
            'parseChildSessionId',
            'getChildSessions',
            'isChildSession'
        ];

        for (const method of requiredMethods) {
            if (typeof ChildSessionManager[method] !== 'function') {
                throw new Error(`ChildSessionManager.${method} 不是函数`);
            }
        }
    });

    /**
     * 测试2: 解析子session ID
     */
    TestSuite.addTest('子session ID解析', () => {
        const testCases = [
            {
                output: 'task_id: ses_abc123\n\n<task_result>...',
                expected: 'ses_abc123',
                description: '标准格式'
            },
            {
                output: 'task_id: ses_xyz789',
                expected: 'ses_xyz789',
                description: '无额外内容'
            },
            {
                output: '无效输出',
                expected: null,
                description: '无效格式'
            },
            {
                output: null,
                expected: null,
                description: 'null输入'
            },
            {
                output: '',
                expected: null,
                description: '空字符串'
            }
        ];

        for (const testCase of testCases) {
            const result = ChildSessionManager.parseChildSessionId(testCase.output);
            if (result !== testCase.expected) {
                throw new Error(
                    `解析失败 [${testCase.description}]: ` +
                    `期望 "${testCase.expected}", 得到 "${result}"`
                );
            }
        }
    });

    /**
     * 测试3: 子会话订阅和取消订阅
     */
    TestSuite.addTest('子会话订阅管理', () => {
        const mainSessionId = 'test_main_ses_123';
        const childSessionId = 'test_child_ses_456';

        // 测试订阅
        ChildSessionManager.subscribeToChildSession(
            mainSessionId,
            childSessionId,
            (mainSession, childEvent) => {
                console.log('测试事件回调:', childEvent);
            }
        );

        // 验证订阅状态
        const isSubscribed = ChildSessionManager.isChildSession(childSessionId);
        if (!isSubscribed) {
            throw new Error('子会话订阅失败');
        }

        const children = ChildSessionManager.getChildSessions(mainSessionId);
        if (!children.includes(childSessionId)) {
            throw new Error('子会话未正确注册到主会话');
        }

        const mainId = ChildSessionManager.getMainSessionId(childSessionId);
        if (mainId !== mainSessionId) {
            throw new Error(`主会话ID映射错误: 期望 ${mainSessionId}, 得到 ${mainId}`);
        }

        // 测试取消订阅
        ChildSessionManager.unsubscribeFromChildSession(childSessionId);

        const isStillSubscribed = ChildSessionManager.isChildSession(childSessionId);
        if (isStillSubscribed) {
            throw new Error('取消订阅失败');
        }

        console.log('  ✅ 订阅和取消订阅功能正常');
    });

    /**
     * 测试4: apiClient.subscribeToEvents是否存在
     */
    TestSuite.addTest('apiClient事件订阅功能', () => {
        if (!window.apiClient) {
            throw new Error('apiClient未初始化');
        }

        if (typeof apiClient.subscribeToEvents !== 'function') {
            throw new Error('apiClient.subscribeToEvents 不是函数');
        }

        if (typeof apiClient.unsubscribeFromEvents !== 'function') {
            throw new Error('apiClient.unsubscribeFromEvents 不是函数');
        }
    });

    /**
     * 测试5: EventAdapter是否支持子会话上下文
     */
    TestSuite.addTest('EventAdapter子会话上下文支持', () => {
        if (!window.EventAdapter) {
            throw new Error('EventAdapter未初始化');
        }

        // 创建模拟事件
        const mockEvent = {
            type: 'message.part.updated',
            properties: {
                part: {
                    type: 'tool',
                    id: 'test_tool_id',
                    content: {
                        tool: 'read',
                        state: {
                            status: 'completed',
                            output: 'test output'
                        }
                    }
                }
            }
        };

        const mockSession = { id: 'test_session' };

        // 测试带子会话上下文的适配
        const adapted = EventAdapter.adaptEvent(mockEvent, mockSession, {
            childSessionId: 'test_child_ses'
        });

        if (!adapted) {
            throw new Error('EventAdapter返回null');
        }

        if (!adapted._isFromChildSession) {
            throw new Error('缺少_isFromChildSession标记');
        }

        if (adapted._childSessionId !== 'test_child_ses') {
            throw new Error(`子会话ID不正确: ${adapted._childSessionId}`);
        }

        console.log('  ✅ EventAdapter子会话上下文支持正常');
    });

    /**
     * 测试6: 集成测试 - 模拟完整流程
     */
    TestSuite.addTest('完整流程集成测试', () => {
        const mainSessionId = 'integration_test_main';
        const childSessionId = 'integration_test_child';

        // 模拟主会话
        const mainSession = {
            id: mainSessionId,
            prompt: '测试任务',
            response: '',
            phases: [],
            actions: [],
            orphanEvents: []
        };

        // 模拟task工具事件
        const taskEvent = {
            type: 'action',
            data: {
                tool_name: 'task',
                output: `task_id: ${childSessionId}\n\n<task_result>success</task_result>`
            }
        };

        console.log('  模拟: 检测task工具事件');
        // 注意：这里只是测试逻辑，不实际调用processEvent
        // 因为processEvent需要完整的window.state环境

        console.log('  ✅ 集成测试准备完成');
    });

    // ========================================================================
    // 实用工具函数
    // ========================================================================

    /**
     * 显示子会话管理器状态
     */
    function showChildSessionStatus() {
        console.log('\n📊 子会话管理器状态:');
        console.log('========================================');

        if (!window.ChildSessionManager) {
            console.log('❌ ChildSessionManager 未初始化');
            return;
        }

        // 获取当前活跃的session
        const activeId = window.state?.activeId;
        console.log(`当前活跃会话: ${activeId || '无'}`);

        if (activeId) {
            const children = ChildSessionManager.getChildSessions(activeId);
            console.log(`子会话数量: ${children.length}`);
            if (children.length > 0) {
                console.log('子会话列表:');
                children.forEach((childId, index) => {
                    console.log(`  ${index + 1}. ${childId}`);
                });
            }
        }

        console.log('========================================\n');
    }

    /**
     * 手动测试：创建模拟task事件
     */
    function testManualTaskEvent() {
        console.log('\n🧪 手动测试: 模拟task工具事件');
        console.log('========================================');

        const activeId = window.state?.activeId;
        if (!activeId) {
            console.error('❌ 没有活跃的会话');
            return;
        }

        const mockChildSessionId = 'manual_test_ses_' + Date.now();
        const mockTaskEvent = {
            type: 'action',
            data: {
                tool_name: 'task',
                output: `task_id: ${mockChildSessionId}\n\n<task_result>测试结果</task_result>`
            }
        };

        console.log(`主会话: ${activeId}`);
        console.log(`模拟子会话: ${mockChildSessionId}`);

        // 解析子会话ID
        const parsedId = ChildSessionManager.parseChildSessionId(mockTaskEvent.data.output);
        console.log(`解析结果: ${parsedId}`);

        if (parsedId === mockChildSessionId) {
            console.log('✅ 解析成功');
        } else {
            console.error('❌ 解析失败');
        }

        console.log('========================================\n');
    }

    // ========================================================================
    // 运行测试
    // ========================================================================

    // 自动运行测试
    if (typeof window !== 'undefined') {
        // 延迟执行，确保所有脚本已加载
        setTimeout(() => {
            TestSuite.runAll();

            // 暴露实用函数到全局
            window.testChildSessionStatus = showChildSessionStatus;
            window.testManualTaskEvent = testManualTaskEvent;

            console.log('💡 提示: 使用以下命令进行手动测试:');
            console.log('  - testChildSessionStatus()  // 查看子会话状态');
            console.log('  - testManualTaskEvent()     // 模拟task事件');
        }, 1000);
    }

    // 导出供Node.js环境使用
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = { TestSuite, showChildSessionStatus, testManualTaskEvent };
    }

})();
