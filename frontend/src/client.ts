let token = '';
export function setToken(value: string) { token = value; }
export async function request(path: string, method = 'GET', body?: any): Promise<any> {
  const headers: Record<string,string> = { Authorization: `Bearer ${token}` };
  if (body && !(body instanceof FormData)) headers['Content-Type'] = 'application/json';
  const response = await fetch(`/api${path}`, { method, headers, body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail || `Request failed (${response.status})`));
  }
  return response.json();
}
export async function download(path: string): Promise<Blob> {
  const response = await fetch(`/api${path}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error(`Download failed (${response.status})`);
  return response.blob();
}
