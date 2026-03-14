// Test Feishu encoding
async function testFeishu() {
    const webhookUrl = 'https://open.feishu.cn/open-apis/bot/v2/hook/899e8328-4975-4241-86e1-2c3837b3a313';

    const message = 'opencode 编码测试：这是一条中文消息';

    const payload = {
        msg_type: 'text',
        content: {
            text: message
        }
    };

    console.log('Sending message:', message);
    console.log('Payload:', JSON.stringify(payload, null, 2));

    try {
        const response = await fetch(webhookUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        console.log('Response:', data);
    } catch (error) {
        console.error('Error:', error);
    }
}

testFeishu();
