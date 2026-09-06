// Typed-ish API client for tracklab's backend (Stage 7).
//
// VITE_API_KEY ending up in the built JS bundle is a deliberate,
// proportionate choice here -- this key gates a single-user, LAN-
// exposed tool against casual access from other devices on the same
// wifi (CLAUDE.md), not a secret being protected *from* the frontend.
// This is a different situation from the Claude API key (Tier 2,
// not yet built): that key must never reach frontend code at all,
// since it would be a real, valuable secret visible to anyone
// inspecting network traffic. Only Vite-prefixed (VITE_*) variables
// are exposed to client code in the first place -- a deliberate
// safety default meant to stop other, real secrets in a .env file
// leaking into the bundle by accident.

const BASE_URL = import.meta.env.VITE_API_BASE_URL;
const API_KEY = import.meta.env.VITE_API_KEY;

const headers = { "X-API-Key": API_KEY };

async function parseOrThrow(response) {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

export async function uploadTrack(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${BASE_URL}/tracks`, {
    method: "POST",
    headers,
    body: formData,
  });
  return parseOrThrow(response);
}

export async function getTrack(id) {
  const response = await fetch(`${BASE_URL}/tracks/${id}`, { headers });
  return parseOrThrow(response);
}
