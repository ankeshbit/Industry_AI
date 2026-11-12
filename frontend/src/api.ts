/**
 * API Client for INDUSTRIA AI Backend (PRD v1.2 §13)
 */

// .env.example documents VITE_API_BASE_URL, but it was never read; default keeps the dev proxy / nginx setup working
const BASE_URL: string = (import.meta.env.VITE_API_BASE_URL as string | undefined) || '/api/v1';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  organisation: {
    id: string;
    name: string;
    slug: string;
  };
}

export interface Job {
  id: string;
  job_type: string;
  status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'RETRY_WAIT';
  progress_percent: number;
  current_step: string;
  attempt?: number;
  error_code?: string;
  user_message?: string;
  created_at: string;
  finished_at?: string;
}

export interface ModelEvaluationItem {
  split: string;
  metric_name: string;
  metric_value: number;
  ci_low?: number;
  ci_high?: number;
  n_samples?: number;
}

export interface ModelInfo {
  id: string;
  registry_name: string;
  version: string;
  pipeline: string;
  configuration: string;
  algorithm: string;
  stage: string;
  training_domain: string;
  reference_evaluations: ModelEvaluationItem[];
  customer_specific_validation: any;
  model_card_uri?: string;
}

export interface DatasetItem {
  id: string;
  machine_id: string;
  name: string;
  dataset_type: string;
  created_at: string;
}

export interface Machine {
  id: string;
  asset_tag: string;
  name: string;
  category_code: string;
  plant_id: string;
  manufacturer?: string;
  model_number?: string;
  serial_number?: string;
  install_date?: string;
  archived_at?: string;
  created_at: string;
}

export interface CompatibilityCheck {
  id: string;
  dataset_version_id: string;
  machine_id: string;
  profile: {
    id: string;
    profile_id: string;
    version: string;
    pipeline: string;
    configuration: string;
  };
  compatibility: {
    status: 'COMPATIBLE' | 'COMPATIBLE_WITH_WARNINGS' | 'INCOMPATIBLE' | 'INSUFFICIENT_DATA' | 'UNSUPPORTED_FORMAT';
    reasons: Array<{
      code: string;
      severity: string;
      feature?: string;
      observed?: any;
      expected?: any;
      message: string;
      remedy?: string;
    }>;
  };
  applicability: {
    level: 'IN_REFERENCE_RANGE' | 'PARTLY_OUTSIDE_REFERENCE_RANGE' | 'MOSTLY_OUTSIDE_REFERENCE_RANGE' | 'NOT_ASSESSED';
    flagged_row_fraction: number;
    per_feature: Record<string, number>;
    domain_note: string;
    disclaimer: string;
  };
  reliability: {
    tier: 'REFERENCE_ONLY' | 'CUSTOMER_VALIDATED' | 'NOT_APPLICABLE';
    statement: string;
  };
  requires_acknowledgement: string[];
  requires_limitation_acknowledgement: boolean;
  created_at: string;
}

export interface AnalysisResult {
  id: string;
  machine_id: string;
  pipeline: string;
  configuration: string;
  result_version: number;
  is_latest: boolean;
  provenance: {
    dataset: { id: string; name: string; version: number; provenance: string };
    profile: string;
    model: { registry_name: string; version: string; training_domain: string; trained_on: string };
    computed_at: string;
  };
  trust: {
    compatibility: string;
    applicability: string;
    reliability_tier: string;
    label: string;
  };
  semantics: string;
  evaluation_sections: {
    reference_dataset_evaluation: { model_card_uri: string | null };
    customer_specific_validation: null;
  };
  summary: {
    total_rows: number;
    predicted_failures: number;
    failure_rate: number;
    mean_failure_probability: number;
    threshold_used: number;
    risk_distribution: { LOW: number; MEDIUM: number; HIGH: number };
  };
  ood_summary: {
    total_rows: number;
    flagged_rows: number;
    flagged_fraction: number;
    per_feature: Record<string, number>;
  };
  limitations: string[];
  explanation_disclaimer: string;
  advisory_notice?: string;
  created_at: string;
}

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// Access tokens live 15 minutes (backend ACCESS_TOKEN_EXPIRE_MINUTES). Previously the stored refresh
// token was never used, so users were silently broken after 15 minutes. Share one in-flight refresh.
let refreshInFlight: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) return false;
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch(`${BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!res.ok) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          return false;
        }
        const data = await res.json();
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        return true;
      } catch {
        return false;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

/** fetch() that retries once with a refreshed access token on 401 (skipped for auth endpoints). */
async function authedFetch(url: string, init: RequestInit): Promise<Response> {
  const build = (): RequestInit => ({
    ...init,
    headers: { ...(init.headers as Record<string, string>), ...getAuthHeader() },
  });
  let res = await fetch(url, build());
  if (res.status === 401 && !url.includes('/auth/') && (await refreshAccessToken())) {
    res = await fetch(url, build());
  }
  return res;
}

export async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  const res = await authedFetch(url, { ...options, headers });
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw errorJson.error || { message: res.statusText, status: res.status };
  }
  return res.json();
}

// Authentication API
export const api = {
  auth: {
    register: (data: { organisation_name: string; email: string; full_name: string; password: string }) =>
      request('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
    login: async (credentials: { email: string; password: string }) => {
      const data = await request<{ access_token: string; refresh_token: string; user: User }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(credentials),
      });
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      return data;
    },
    getMe: () => request<User>('/users/me'),
    logout: () => {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        // Best-effort server-side revocation of the refresh token family member
        fetch(`${BASE_URL}/auth/logout`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        }).catch(() => undefined);
      }
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    },
  },

  machines: {
    list: () => request<Machine[]>('/machines'),
    get: (id: string) => request<Machine>(`/machines/${id}`),
    create: (data: { asset_tag: string; name: string; category_code: string; manufacturer?: string; model_number?: string }) =>
      request<Machine>('/machines', { method: 'POST', body: JSON.stringify(data) }),
    archive: (id: string) => request(`/machines/${id}/archive`, { method: 'POST' }),
    categories: () => request<Array<{ code: string; name: string }>>('/machine-categories'),
  },

  datasets: {
    listForMachine: (machineId: string) =>
      request<DatasetItem[]>(`/machines/${machineId}/datasets`),
    createForMachine: (machineId: string, data: { name: string; dataset_type?: string }) =>
      request<{ id: string; name: string }>(`/machines/${machineId}/datasets`, { method: 'POST', body: JSON.stringify(data) }),
    upload: async (datasetId: string, file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      const res = await authedFetch(`${BASE_URL}/datasets/${datasetId}/versions/upload`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const error = await res.json().catch(() => ({ error: { message: res.statusText } }));
        throw error.error || { message: res.statusText };
      }
      return res.json();
    },
    getVersion: (vid: string) => request<any>(`/dataset-versions/${vid}`),
    getPreview: (vid: string) => request<{ preview: any[] }>(`/dataset-versions/${vid}/preview`),
    getSuggestions: (vid: string, profileId: string) =>
      request<{ suggestions: Record<string, any> }>(`/dataset-versions/${vid}/mappings/${profileId}/suggestions`),
    saveMapping: (vid: string, profileId: string, mappings: any) =>
      request(`/dataset-versions/${vid}/mappings/${profileId}`, { method: 'PUT', body: JSON.stringify({ mappings }) }),
    getValidationReport: (vid: string) => request<any>(`/dataset-versions/${vid}/validation-reports`),
  },

  compatibility: {
    runChecks: (vid: string, profileId?: string) =>
      request<CompatibilityCheck[]>(`/dataset-versions/${vid}/compatibility-checks`, {
        method: 'POST',
        body: JSON.stringify({ profile_id: profileId }),
      }),
    acknowledgeWarnings: (checkId: string, reasonCodes: string[]) =>
      request(`/compatibility-checks/${checkId}/acknowledge-warnings`, {
        method: 'POST',
        body: JSON.stringify({ reason_codes: reasonCodes }),
      }),
    acknowledgeLimitation: (machineId: string, profileUuid: string) =>
      request('/limitations/acknowledge', {
        method: 'POST',
        body: JSON.stringify({ machine_id: machineId, profile_uuid: profileUuid }),
      }),
  },

  analyses: {
    run: (checkId: string, acknowledgedWarnings: string[], limitationAcknowledged: boolean) =>
      request<{ job_id: string; status: string; analysis_result_id?: string }>('/analyses', {
        method: 'POST',
        body: JSON.stringify({
          compatibility_check_id: checkId,
          acknowledged_reason_codes: acknowledgedWarnings,
          limitation_acknowledged: limitationAcknowledged,
        }),
      }),
    get: (resultId: string) => request<AnalysisResult>(`/analyses/${resultId}`),
    getRows: (resultId: string) => request<{ analysis_id: string; total_rows: number; top_rows: any[] }>(`/analyses/${resultId}/rows`),
    getMachineAnalyses: (machineId: string) => request<AnalysisResult[]>(`/machines/${machineId}/analyses`),
  },

  models: {
    list: () => request<ModelInfo[]>('/models'),
    getTemplate: async (profileId: string) => {
      const res = await authedFetch(`${BASE_URL}/pipeline-profiles/${profileId}/template`, { method: 'GET' });
      if (!res.ok) throw new Error('Failed to download template.');
      return res.text();
    },
  },

  jobs: {
    list: () => request<Job[]>('/jobs'),
    get: (id: string) => request<Job>(`/jobs/${id}`),
  },
};

