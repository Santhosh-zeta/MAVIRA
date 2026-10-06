// Typed client for the MAVIRA API (all calls go through the same-origin proxy).

export type Tier = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Usage = "YES" | "NO" | "INCONCLUSIVE";
export type RiskClass = "NONE_IDENTIFIED" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface Effective {
  criticality_tier?: Tier; ai_usage?: Usage; risk_class?: RiskClass; risk_score?: number;
  review_status?: string; override_reason?: string; override_by?: string; reviewed_by?: string; reviewed_at?: string;
  risk_rationale?: string; ai_usage_summary?: string;
}

export interface AssessmentSummary {
  id: string; run_id: string; vendor_id: string; status: string; stage: string | null;
  criticality_tier: Tier | null; criticality_score: number | null; depth_tier: Tier | null;
  ai_usage: Usage | null; ai_confidence: number | null; ai_types: string[];
  risk_class: RiskClass | null; risk_score: number | null; evidence_strength_level: string | null;
  top_evidence_strength: number | null; provider_status: string | null; review_status: string;
  human_review_required: boolean; completed_at: string | null; effective: Effective; errors: { stage?: string; error: string }[];
  vendor_ref?: string; vendor_name?: string; category?: string;
}

export interface SourceRef {
  id: string; url: string; domain: string; title: string | null; source_type: string | null;
  reliability_level: string | null; reliability_score: number | null; published_date: string | null;
  retrieved_at: string | null; collection_method: "LIVE" | "CACHED" | "DEMO_MOCK"; cache_origin: string | null;
  status: string; content_hash: string | null; content?: string; error?: string | null;
  category?: string; from_cache?: boolean; ai_relevant_chunks?: number;
}

export interface EvidenceItem {
  id: string; assessment_id: string; vendor_ref: string | null; vendor_name: string | null; claim: string;
  exact_excerpt: string; excerpt_start: number | null; excerpt_end: number | null; validation_status: string;
  rejection_reason: string | null; nature: string; ai_types: string[]; interpretation: string; directness: string;
  service_relevance: number; strength_score: number | null; strength_level: string | null;
  strength_breakdown: Record<string, { value: number; weight: number; points: number }> | null;
  confidence: number | null; proposed_by: string; source: SourceRef;
}

export interface Factor { key: string; label: string; score: number; weight: number; contribution: number; basis: string; matched_rule: string | null }

export interface AssessmentDetail extends AssessmentSummary {
  vendor: { id: string; vendor_ref: string; name: string; description: string; service: string; category: string;
    website: string; business_process: string; operational_dependency: string; data_classification: string; data_volume: string; import_id: string };
  run: { id: string; osint_mode: string; search_provider: string; analyzer: string; model_name: string | null;
    prompt_version: string | null; methodology_version: string; created_at: string; completed_at: string | null };
  criticality_factors: { score: number; tier: Tier; weighted_tier: Tier; factors: Record<string, Factor>;
    escalations: { rule: string; description: string; from: string; to: string }[] } | null;
  criticality_rationale: string;
  depth_plan: { tier: Tier; label: string; rationale: string; source_categories: string[]; max_sources: number;
    min_independent_sources: number; negative_evidence_review: boolean; provider_investigation: boolean;
    human_review_required: boolean; description: string; queries: { category: string; query: string }[] } | null;
  ai_usage_summary: string; ai_usage_basis: string;
  negative_evidence: { sources_checked: number; searches_performed: number; assessment_scope: string[];
    statement: string | null; sources_without_ai_content: string[] } | null;
  risk_rationale: string;
  risk_inputs: { result: { ai_presence: number; floors: { rule: string; description: string; from: string; to: string }[] } } | null;
  stage_log: { stage: string; label: string; status: string; at: string }[];
  evidence: EvidenceItem[];
  providers: { provider_name: string; provider_type: string; confidence: number; service_linkage: string; evidence_id: string; evidence_excerpt: string }[];
  risk_factors: { category: string; score: number; weight: number; contribution: number; status: string; rationale: string }[];
  recommendations: { rule_id: string; priority: string; category: string; action: string; due_in_days: number; grounded_on: { evidence_ids: string[] } }[];
  reviews: { id: string; decision: string; analyst: string; reason: string | null; overrides: Record<string, string> | null;
    original_snapshot: Record<string, unknown>; reassessment_run_id: string | null; created_at: string }[];
  sources: SourceRef[];
  searches: { category: string; query: string; provider: string; status: string; result_count: number; latency_ms: number | null; error: string | null }[];
}

export interface RunInfo {
  id: string; import_id: string; status: string; osint_mode: string; search_provider: string; analyzer: string;
  methodology_version: string; total_vendors: number; completed_vendors: number; failed_vendors: number;
  errors: { vendor?: string; error: string }[]; created_at: string; completed_at: string | null; parent_run_id: string | null;
  triggered_by: string;
}

export interface RunDetail extends RunInfo {
  progress: number;
  assessments: (AssessmentSummary & { vendor_ref: string; vendor_name: string;
    stages: { key: string; label: string; done: boolean }[] })[];
}

export interface Dashboard {
  import: { id: string; filename: string; uploaded_at: string } | null;
  totals: { vendors: number; assessed: number; ai_confirmed: number; ai_inconclusive: number; high_critical_risk: number; pending_review: number };
  criticality_distribution: Record<string, number>;
  risk_distribution: Record<string, number>;
  vendors: AssessmentSummary[];
  recent_runs: RunInfo[];
}

export interface Health { status: string; osint_mode: string; search_provider: string; analyzer: string; llm_enabled: boolean; data_egress: string[] }

export class ApiError extends Error {}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      msg = body.error ?? msg;
    } catch { /* non-JSON error */ }
    throw new ApiError(msg);
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T,>(path: string) => fetch(`/api${path}`, { cache: "no-store" }).then((r) => handle<T>(r)),
  post: <T,>(path: string, body: unknown) =>
    fetch(`/api${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then((r) => handle<T>(r)),
  put: <T,>(path: string, body: unknown, analyst?: string) =>
    fetch(`/api${path}`, { method: "PUT", headers: { "Content-Type": "application/json", ...(analyst ? { "X-Analyst": analyst } : {}) },
      body: JSON.stringify(body) }).then((r) => handle<T>(r)),
  upload: <T,>(file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetch(`/api/imports`, { method: "POST", body: fd }).then((r) => handle<T>(r));
  },
};
