const CLIENT_ID_KEY = 'flight_tracker_client_id';

export function getClientId(): string {
  let id = localStorage.getItem(CLIENT_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(CLIENT_ID_KEY, id);
  }
  return id;
}

export function getAuthHeaders(): Record<string, string> {
  return { 'X-Client-ID': getClientId() };
}
