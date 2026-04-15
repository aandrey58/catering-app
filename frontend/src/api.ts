import type { Day, Feedback, SelectionPayload, WeeksResponse } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export const ACCESS_TOKEN_KEY = "access_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setAccessToken(token: string | null): void {
  if (token) {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
  }
}

function errorMessageFromPayload(payload: unknown): string {
  if (payload && typeof payload === "object") {
    const p = payload as Record<string, unknown>;
    if (typeof p.message === "string") return p.message;
    if (typeof p.error === "string") return p.error;
    const detail = p.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object") {
      const d = detail as Record<string, unknown>;
      if (typeof d.message === "string") return d.message;
      if (typeof d.error === "string") return d.error;
    }
  }
  return "Request failed";
}

function authHeaders(includeJson = true): HeadersInit {
  const headers: Record<string, string> = {};
  if (includeJson) {
    headers["Content-Type"] = "application/json";
  }
  const t = getAccessToken();
  if (t) {
    headers.Authorization = `Bearer ${t}`;
  }
  return headers;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: { ...authHeaders(), ...(options?.headers as Record<string, string>) }
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(errorMessageFromPayload(payload));
  }
  return payload as T;
}

export type LoginResponse = {
  status: "ok";
  login: string;
  note: string;
  access_token: string;
  token_type: string;
};

export async function login(loginValue: string, password: string) {
  const response = await fetch(`${API_BASE_URL}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ login: loginValue, password })
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(errorMessageFromPayload(payload));
  }
  return payload as LoginResponse;
}

export async function getMe() {
  return request<{ login: string; note: string }>("/me");
}

export async function getWeeks() {
  return request<WeeksResponse>("/weeks");
}

export async function getMenu() {
  return request<string[][]>("/menu?sheet=eng");
}

export async function getMenuEnabled() {
  return request<{ enabled: boolean }>("/menu_enabled");
}

export async function getSelections(day: Day) {
  return request<{ selections: SelectionPayload | null }>("/get_selections", {
    method: "POST",
    body: JSON.stringify({ day })
  });
}

export async function saveSelections(day: Day, selections: SelectionPayload) {
  return request<{ success: boolean; message: string }>("/save", {
    method: "POST",
    body: JSON.stringify({ day, selections })
  });
}

export async function deleteSelections(day: Day) {
  return request<{ deleted: boolean; message?: string }>("/delete", {
    method: "POST",
    body: JSON.stringify({ day })
  });
}

export async function getFeedback() {
  return request<{ feedback: Feedback | null }>("/get_feedback", {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function saveFeedback(rating: number, feedbackText: string) {
  return request<{ success: boolean; message: string }>("/save_feedback", {
    method: "POST",
    body: JSON.stringify({ rating, feedback_text: feedbackText })
  });
}

export async function deleteFeedback() {
  return request<{ deleted: boolean; message?: string }>("/delete_feedback", {
    method: "POST",
    body: JSON.stringify({})
  });
}
