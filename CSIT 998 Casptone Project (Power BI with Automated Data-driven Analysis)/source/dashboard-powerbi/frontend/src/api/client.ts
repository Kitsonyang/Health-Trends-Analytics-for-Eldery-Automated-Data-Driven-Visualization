/**
 * API Client Module
 * 
 * Centralized HTTP client for all backend API communication. Provides
 * type-safe wrappers for REST endpoints with automatic authentication,
 * timeout handling, and error normalization.
 * 
 * Key Features:
 * - Automatic bearer token injection for authenticated requests
 * - 10-second timeout to prevent browser freeze on network issues
 * - Type-safe request/response interfaces
 * - Consistent error handling and message extraction
 * - Token management utilities for auth workflows
 * 
 * Architecture:
 * - Uses relative paths by default for Nginx reverse proxy setup
 * - All authenticated requests include Authorization header automatically
 * - Response errors normalized to Error objects with status/body properties
 * 
 * @module api/client
 */

/**
 * API base URL, defaults to relative path for Nginx proxy.
 * Can be overridden via VITE_API_BASE environment variable for development.
 */
export const API_BASE = (import.meta as any).env?.VITE_API_BASE || '';

/**
 * Global API request timeout to prevent indefinite hangs.
 * Protects against server downtime or network issues freezing the UI.
 */
const API_TIMEOUT = 60000; // 60 seconds for file uploads

const TOKEN_KEY = 'auth_token';

export function setAuthToken(token: string | null) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function clearAuthToken() {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * Fetch wrapper with automatic timeout using AbortController.
 * 
 * Prevents requests from hanging indefinitely when backend is down or
 * network is slow. Converts timeout to user-friendly error message.
 * 
 * @param url - Full request URL
 * @param options - Standard fetch options
 * @returns Response object if successful within timeout
 * @throws Error with timeout message if request exceeds API_TIMEOUT
 */
async function fetchWithTimeout(url: string, options: RequestInit = {}): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error: any) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error(`Request timeout after ${API_TIMEOUT}ms`);
    }
    throw error;
  }
}

/**
 * Normalize HTTP responses into consistent TypeScript types.
 * 
 * Extracts error messages from FastAPI response format (detail field)
 * and attaches status code + raw body to Error object for debugging.
 * 
 * @param res - Raw fetch Response object
 * @returns Parsed JSON response body for successful requests
 * @throws Error with extracted message for failed requests (status >= 400)
 */
async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    let body: any = text;
    try { body = text ? JSON.parse(text) : text; } catch { /* keep text */ }
    const err: any = new Error((body && body.detail) || text || `HTTP ${res.status}`);
    err.status = res.status;
    err.body = body;
    throw err;
  }
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) return res.json();
  return (res as unknown) as any;
}

/**
 * HTTP GET request with automatic authentication.
 * 
 * @param path - API endpoint path (relative to API_BASE)
 * @param init - Optional fetch configuration
 * @returns Typed response body
 * @throws Error if request fails or times out
 */
export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const token = getAuthToken();
  const headers: HeadersInit = { 'Accept': 'application/json', ...(init?.headers || {}) };
  
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }
  
  const res = await fetchWithTimeout(url, {
    method: 'GET',
    headers,
    ...init,
  });
  return handleResponse<T>(res);
}

/**
 * HTTP POST request with automatic authentication and JSON serialization.
 * 
 * @param path - API endpoint path (relative to API_BASE)
 * @param body - Request payload (will be JSON.stringify'd)
 * @param init - Optional fetch configuration
 * @returns Typed response body
 * @throws Error if request fails or times out
 */
export async function apiPost<T>(path: string, body?: any, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const token = getAuthToken();
  const headers: HeadersInit = { 'Content-Type': 'application/json', 'Accept': 'application/json', ...(init?.headers || {}) };
  
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }
  
  const res = await fetchWithTimeout(url, {
    method: 'POST',
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    ...init,
  });
  return handleResponse<T>(res);
}

/**
 * HTTP PUT request with automatic authentication and JSON serialization.
 * 
 * @param path - API endpoint path (relative to API_BASE)
 * @param body - Request payload (will be JSON.stringify'd)
 * @param init - Optional fetch configuration
 * @returns Typed response body
 * @throws Error if request fails or times out
 */
export async function apiPut<T>(path: string, body?: any, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const token = getAuthToken();
  const headers: HeadersInit = { 'Content-Type': 'application/json', 'Accept': 'application/json', ...(init?.headers || {}) };
  
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }
  
  const res = await fetchWithTimeout(url, {
    method: 'PUT',
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    ...init,
  });
  return handleResponse<T>(res);
}

/**
 * Utility to construct full image URLs from backend paths.
 * 
 * @param path - Image path from backend (e.g., "/static/chart.png")
 * @returns Full URL with API_BASE prepended
 */
export function imageUrl(path: string): string {
  return `${API_BASE}${path}`;
}

// ==================== Power BI API ====================

export interface PowerBIRefreshResponse {
  ok: boolean;
  dataset_id: string;
  status_code: number;
}

export interface PowerBIRefreshStatusResponse {
  ok: boolean;
  dataset_id: string;
  today_count?: number;      // Refreshes completed today (for quota tracking)
  total?: number;             // Total refresh count
  latest?: any;               // Most recent refresh record
  history?: any[];            // Historical refresh records
}

/**
 * Trigger Power BI dataset refresh via Azure REST API.
 * 
 * Initiates asynchronous refresh of Power BI dataset. Use powerbiRefreshStatus()
 * to poll for completion. Subject to daily limits (Pro: 8, PPU/Premium: 48).
 * 
 * @param params - Optional dataset ID and notification settings
 * @returns Confirmation with dataset ID and HTTP status
 * 
 * @remarks
 * Backend proxies to https://api.powerbi.com/v1.0/myorg/datasets/{id}/refreshes
 * Authentication handled server-side via service principal.
 */
export async function powerbiTriggerRefresh(params?: { datasetId?: string; notifyOption?: string }): Promise<PowerBIRefreshResponse> {
  const body: any = {};
  if (params?.datasetId) body.dataset_id = params.datasetId;
  if (params?.notifyOption) body.notify_option = params.notifyOption;
  return apiPost<PowerBIRefreshResponse>('/api/powerbi/datasets/refresh', body);
}

/**
 * Check Power BI dataset refresh status and history.
 * 
 * Returns current refresh state, today's quota usage, and recent history.
 * Used for polling after trigger and displaying refresh history page.
 * 
 * @param datasetId - Optional dataset ID (uses default from env if omitted)
 * @returns Status object with latest refresh and today's count
 */
export async function powerbiRefreshStatus(datasetId?: string): Promise<PowerBIRefreshStatusResponse> {
  const q = datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}` : '';
  return apiGet<PowerBIRefreshStatusResponse>(`/api/powerbi/datasets/refresh/status${q}`);
}

/**
 * Fetch Power BI access token (for debugging purposes).
 * 
 * @returns Partial token preview and optionally full token
 * @internal
 */
export async function powerbiGetTokenPreview(): Promise<{ ok: boolean; token_preview: string; token?: string }> {
  return apiGet<{ ok: boolean; token_preview: string; token?: string }>(`/api/powerbi/token`);
}

/**
 * Fetch raw Power BI refresh records from Azure API.
 * 
 * @param datasetId - Optional dataset ID
 * @returns Raw refresh history from Power BI service
 * @internal
 */
export async function powerbiRefreshRecordsRaw(datasetId?: string): Promise<any> {
  const q = datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}` : '';
  return apiGet<any>(`/api/powerbi/datasets/refresh/records${q}`);
}


// ==================== Authentication API ====================

export interface RegisterRequest {
  username: string;           // Min 3 chars, trimmed
  password: string;           // Min 6 chars, hashed server-side with SHA-256
  role?: string;              // 'user' or 'admin', defaults to 'user'
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  ok: boolean;
  token: string;              // Bearer token for Authorization header
  user: {
    id: number;
    username: string;
    role: string;             // 'user' or 'admin'
    created_at: string;
  };
}

export interface UserResponse {
  ok: boolean;
  user: {
    id: number;
    username: string;
    role: string;
    created_at: string;
  };
}

export interface MessageResponse {
  ok: boolean;
  message: string;
}

export async function authRegister(data: RegisterRequest): Promise<MessageResponse> {
  return apiPost<MessageResponse>('/api/auth/register', data);
}

export async function authLogin(data: LoginRequest): Promise<LoginResponse> {
  return apiPost<LoginResponse>('/api/auth/login', data);
}

export async function authLogout(): Promise<MessageResponse> {
  return apiPost<MessageResponse>('/api/auth/logout');
}

export async function authGetMe(): Promise<UserResponse> {
  return apiGet<UserResponse>('/api/auth/me');
}

export async function authVerifyToken(): Promise<{ ok: boolean; valid: boolean; user: any }> {
  return apiGet<{ ok: boolean; valid: boolean; user: any }>('/api/auth/verify');
}


