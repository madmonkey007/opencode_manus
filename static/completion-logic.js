(function initCompletionLogic(root) {
  function computeCompletion(adapted, activeAssistantMessageId, sessionError, sessionIdleSeen) {
    const isError = sessionError || adapted?.value === 'error' || adapted?.status === 'error';
    const isAssistantCompletion =
      adapted?.type === 'message_updated' &&
      adapted?.time?.completed &&
      adapted?.role === 'assistant' &&
      (!activeAssistantMessageId || adapted?.message_id === activeAssistantMessageId);
    const isDone = isAssistantCompletion && !!sessionIdleSeen;

    return { isDone, isError, isAssistantCompletion };
  }

  function computeCompletionDecision(
    adapted,
    activeAssistantMessageId,
    sessionError,
    sessionIdleSeen,
    lastDeltaAt,
    nowMs,
    quietWindowMs
  ) {
    const result = computeCompletion(adapted, activeAssistantMessageId, sessionError, sessionIdleSeen);
    const hasQuietWindow = Number.isFinite(quietWindowMs) && quietWindowMs > 0;
    const hasLastDelta = typeof lastDeltaAt === 'number';
    const now = typeof nowMs === 'number' ? nowMs : Date.now();
    const quietOk = !hasQuietWindow || !hasLastDelta || now - lastDeltaAt >= quietWindowMs;
    const shouldDefer = result.isAssistantCompletion && (!sessionIdleSeen || !quietOk);
    const isDone = result.isAssistantCompletion && !!sessionIdleSeen && quietOk;

    return { ...result, isDone, shouldDefer, quietOk };
  }

  function resetCompletionState(session) {
    if (!session) return;
    session._sessionIdleSeen = false;
    session._pendingAssistantCompletion = false;
    session._lastAssistantCompletionAdapted = null;
    session._hasToolError = false;
    if (session._completionTimer) {
      clearTimeout(session._completionTimer);
      session._completionTimer = null;
    }
  }

  const api = { computeCompletion, computeCompletionDecision, resetCompletionState };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }

  if (root) {
    root.OpenCodeCompletionLogic = api;
  }
})(typeof window !== 'undefined' ? window : globalThis);
