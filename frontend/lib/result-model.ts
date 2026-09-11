// Pure mapping from the backend task payload to the verdict view model.
//
// This module contains NO verdict data — it only reshapes whatever the backend
// reported, and it is deliberately free of browser/environment dependencies so
// it can be unit-tested under Node (see tests/js/render_test.mjs).

export interface ResultIssue {
  title: string
  severity: 'HIGH' | 'MEDIUM' | 'LOW'
  detail: string
}

export interface ExecutionTraceStep {
  stage: string
  status: string
  timestamp: string
}

export interface RetrievedChunk {
  source: string
  title: string
  snippet: string
}

export interface VerdictModel {
  taskId: string
  permitId: string
  asset: string
  status: string
  ruleResult: string
  llmResult: string
  agreement: string
  finalDecision: string
  requiresHumanReview: boolean
  explanation: string
  ruleChecks: string[]
  ruleIssues: ResultIssue[]
  llmReasoning: string
  llmIssues: ResultIssue[]
  reasoningProvider: string | null
  deterministicEvaluated: boolean
  auditRef: string | null
  executionTrace: ExecutionTraceStep[]
  retrievedKnowledge: RetrievedChunk[]
}

// Structural subset of the backend task payload (see backend/api/tasks.py).
interface VerdictTask {
  task_id: string
  status: string
  permit_id: string
  scenario: string
  audit_ref: string | null
  result: {
    deterministic_safety_evaluated: boolean | null
    rule_result: string | null
    rules_triggered: string[] | null
    conflicting_permit_ids: string[] | null
    rule_explanation: string | null
    llm_result: string | null
    reasoning_provider: string | null
    reasoning_explanation: string | null
    agreement: string | null
    final_decision: string | null
    requires_human_review: boolean | null
    explanation: string | null
    execution_trace: Array<{ stage: string; status: string; timestamp: string }> | null
    retrieved_context: Array<{ source: string; title: string; snippet: string }> | null
  } | null
}

export function buildVerdictModel(task: VerdictTask): VerdictModel {
  const r = task.result

  const conflictIssues: ResultIssue[] = (r?.conflicting_permit_ids ?? []).map((id) => ({
    title: `Conflicting permit ${id}`,
    severity: 'HIGH',
    detail: `The declared work boundary overlaps the scope of active permit ${id}. Energy isolation cannot be guaranteed without reconciliation.`,
  }))

  let llmReasoning = r?.reasoning_explanation ?? ''
  if (!llmReasoning && r?.llm_result === 'UNAVAILABLE') {
    llmReasoning =
      'Local reasoning service was not reachable, so no AI verdict was computed. The deterministic rule evaluation stands unchanged.'
  }

  const ruleChecks: string[] = (r?.rules_triggered ?? []).map(
    (rule) => `Triggered constraint: ${rule}`,
  )
  if (ruleChecks.length === 0 && r?.deterministic_safety_evaluated) {
    ruleChecks.push('All evaluated safety constraints were satisfied.')
  }

  const permitId = task.permit_id || 'PERMIT-UNKNOWN'

  return {
    taskId: task.task_id,
    permitId,
    asset: task.scenario || `Permit ${permitId}`,
    status: task.status,
    ruleResult: r?.rule_result ?? 'UNAVAILABLE',
    llmResult: r?.llm_result ?? 'UNAVAILABLE',
    agreement: r?.agreement ?? 'UNAVAILABLE',
    finalDecision: r?.final_decision ?? 'NOT_EVALUATED',
    requiresHumanReview: r?.requires_human_review ?? false,
    explanation:
      r?.explanation ??
      'No safety analysis has been recorded for this task yet. It may still be queued or awaiting processing.',
    ruleChecks,
    ruleIssues: conflictIssues,
    llmReasoning,
    llmIssues: [],
    reasoningProvider: r?.reasoning_provider ?? null,
    deterministicEvaluated: r?.deterministic_safety_evaluated ?? false,
    auditRef: task.audit_ref,
    executionTrace: (r?.execution_trace ?? []).map((step) => ({
      stage: step.stage,
      status: step.status,
      timestamp: step.timestamp,
    })),
    retrievedKnowledge: (r?.retrieved_context ?? []).map((chunk) => ({
      source: chunk.source,
      title: chunk.title,
      snippet: chunk.snippet,
    })),
  }
}