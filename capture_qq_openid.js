/**
 * QQ Bot Event Listener - Capture OpenID
 *
 * This script listens to QQ bot events and captures user OpenIDs
 * Usage: node capture_qq_openid.js
 */

const express = require('express');
const bodyParser = require('body-parser');

const app = express();
const PORT = 18081; // Different from IM Bridge

app.use(bodyParser.json());

console.log('=' .repeat(60));
console.log('QQ Bot Event Listener - OpenID Capture Tool');
console.log('=' .repeat(60));
console.log();
console.log('Listening on port ' + PORT);
console.log();
console.log('Setup your QQ bot to forward events to:');
console.log(`  http://your-server-ip:${PORT}/qq/events`);
console.log();
console.log('Then send a message to your bot in QQ.');
console.log('Your OpenID will be displayed below.');
console.log('=' .repeat(60));
console.log();

// Event endpoint
app.post('/qq/events', (req, res) => {
    console.log();
    console.log('─'.repeat(60));
    console.log('📥 Received Event');
    console.log('─'.repeat(60));

    const event = req.body;

    // Display the entire event
    console.log('Full Event:');
    console.log(JSON.stringify(event, null, 2));
    console.log();

    // Try to extract OpenID from different possible locations
    const possibleKeys = ['openid', 'open_id', 'user_id', 'userId', 'author_id'];

    for (const key of possibleKeys) {
        if (event[key]) {
            console.log(`✅ Found OpenID in field "${key}":`);
            console.log(`   ${event[key]}`);
            console.log();
            console.log('Add this to your .env.qq:');
            console.log(`QQ_TARGETS=user:${event[key]}`);
            console.log();
        }
    }

    // Check nested objects
    if (event.event && event.event.data) {
        const data = event.event.data;
        for (const key of possibleKeys) {
            if (data[key]) {
                console.log(`✅ Found OpenID in event.data.${key}:`);
                console.log(`   ${data[key]}`);
                console.log();
                console.log('Add this to your .env.qq:');
                console.log(`QQ_TARGETS=user:${data[key]}`);
                console.log();
            }
        }
    }

    // Check message sender
    if (event.message && event.message.sender) {
        const sender = event.message.sender;
        if (sender.user_id || sender.openid || sender.open_id) {
            const openid = sender.user_id || sender.openid || sender.open_id;
            console.log(`✅ Found OpenID in message sender:`);
            console.log(`   ${openid}`);
            console.log();
            console.log('Add this to your .env.qq:');
            console.log(`QQ_TARGETS=user:${openid}`);
            console.log();
        }
    }

    res.json({ received: true });
});

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'ok', message: 'OpenID capture tool running' });
});

app.listen(PORT, () => {
    console.log('✅ Server is listening...');
    console.log();
    console.log('Waiting for QQ bot events...');
    console.log('Send a message to your bot in QQ!');
    console.log();
});
