const assert = require('assert');

const { computeCompletion, computeCompletionDecision, resetCompletionState } = require('../../static/completion-logic');

function testStatusDoesNotComplete() {
  const adapted = { type: 'status', value: 'done' };
  const result = computeCompletion(adapted, 'msg-1');
  assert.strictEqual(result.isDone, false, 'status done should not complete session');
  assert.strictEqual(result.isAssistantCompletion, false, 'status done should not be assistant completion');
}

function testAssistantCompletionMatchesActiveId() {
  const adapted = {
    type: 'message_updated',
    role: 'assistant',
    message_id: 'msg-1',
    time: { completed: true }
  };
  const result = computeCompletion(adapted, 'msg-1', false, true);
  assert.strictEqual(result.isDone, true, 'assistant completion should complete session');
  assert.strictEqual(result.isAssistantCompletion, true, 'assistant completion flag should be true');
}

function testAssistantCompletionMismatchedIdDoesNotComplete() {
  const adapted = {
    type: 'message_updated',
    role: 'assistant',
    message_id: 'msg-2',
    time: { completed: true }
  };
  const result = computeCompletion(adapted, 'msg-1', false, true);
  assert.strictEqual(result.isDone, false, 'mismatched assistant completion should not complete session');
}

function testAssistantCompletionNoActiveIdCompletes() {
  const adapted = {
    type: 'message_updated',
    role: 'assistant',
    message_id: 'msg-2',
    time: { completed: true }
  };
  const result = computeCompletion(adapted, null, false, true);
  assert.strictEqual(result.isDone, true, 'assistant completion should complete session when no active id');
}

function testErrorFlag() {
  const adapted = { type: 'status', value: 'error' };
  const result = computeCompletion(adapted, null, false, false);
  assert.strictEqual(result.isError, true, 'error status should set isError');
}

function testSessionErrorFlag() {
  const adapted = { type: 'message_updated', role: 'assistant', time: { completed: true } };
  const result = computeCompletion(adapted, null, true, false);
  assert.strictEqual(result.isError, true, 'session error should set isError');
}

function testAssistantCompletionRequiresIdle() {
  const adapted = {
    type: 'message_updated',
    role: 'assistant',
    message_id: 'msg-1',
    time: { completed: true }
  };
  const result = computeCompletion(adapted, 'msg-1', false, false);
  assert.strictEqual(result.isDone, false, 'assistant completion should wait for session idle');
  assert.strictEqual(result.isAssistantCompletion, true, 'assistant completion flag should be true');
}

function testAssistantCompletionDefersUntilIdle() {
  const adapted = {
    type: 'message_updated',
    role: 'assistant',
    message_id: 'msg-1',
    time: { completed: true }
  };
  const result = computeCompletionDecision(adapted, 'msg-1', false, false);
  assert.strictEqual(result.shouldDefer, true, 'assistant completion should defer until idle');
  assert.strictEqual(result.isDone, false, 'assistant completion should not complete before idle');
}

function testAssistantCompletionDefersUntilQuietWindow() {
  const adapted = {
    type: 'message_updated',
    role: 'assistant',
    message_id: 'msg-1',
    time: { completed: true }
  };
  const lastDeltaAt = 1000;
  const nowMs = 1200;
  const quietWindowMs = 500;
  const result = computeCompletionDecision(
    adapted,
    'msg-1',
    false,
    true,
    lastDeltaAt,
    nowMs,
    quietWindowMs
  );
  assert.strictEqual(result.shouldDefer, true, 'assistant completion should defer until quiet window');
  assert.strictEqual(result.isDone, false, 'assistant completion should not complete before quiet window');
}

function testAssistantCompletionPassesAfterQuietWindow() {
  const adapted = {
    type: 'message_updated',
    role: 'assistant',
    message_id: 'msg-1',
    time: { completed: true }
  };
  const lastDeltaAt = 1000;
  const nowMs = 2000;
  const quietWindowMs = 500;
  const result = computeCompletionDecision(
    adapted,
    'msg-1',
    false,
    true,
    lastDeltaAt,
    nowMs,
    quietWindowMs
  );
  assert.strictEqual(result.shouldDefer, false, 'assistant completion should not defer after quiet window');
  assert.strictEqual(result.isDone, true, 'assistant completion should complete after quiet window');
}

function testResetCompletionState() {
  const session = {
    _sessionIdleSeen: true,
    _pendingAssistantCompletion: true,
    _lastAssistantCompletionAdapted: { type: 'message_updated' },
    _hasToolError: true
  };
  resetCompletionState(session);
  assert.strictEqual(session._sessionIdleSeen, false, 'reset should clear idle seen');
  assert.strictEqual(session._pendingAssistantCompletion, false, 'reset should clear pending completion');
  assert.strictEqual(session._lastAssistantCompletionAdapted, null, 'reset should clear last completion');
  assert.strictEqual(session._hasToolError, false, 'reset should clear tool error');
}

testStatusDoesNotComplete();
testAssistantCompletionMatchesActiveId();
testAssistantCompletionMismatchedIdDoesNotComplete();
testAssistantCompletionNoActiveIdCompletes();
testErrorFlag();
testSessionErrorFlag();
testAssistantCompletionRequiresIdle();
testAssistantCompletionDefersUntilIdle();
testAssistantCompletionDefersUntilQuietWindow();
testAssistantCompletionPassesAfterQuietWindow();
testResetCompletionState();

console.log('test_completion_logic: OK');
