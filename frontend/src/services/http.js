// Pure helpers (no axios import) so they can be tested on their own.

const NO_LABEL = new Set(["non_field_errors", "detail", "message"]);
const pretty = (key) => key.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

function firstFieldError(obj) {
  if (!obj || typeof obj !== "object" || Array.isArray(obj)) return "";
  for (const [key, value] of Object.entries(obj)) {
    const msg = Array.isArray(value)
      ? value.find((v) => typeof v === "string")
      : typeof value === "string"
        ? value
        : "";
    if (msg) return NO_LABEL.has(key) ? msg : `${pretty(key)}: ${msg}`;
  }
  return "";
}

// Backend error format: { message, errors } where errors is a dict of field messages or null.
export function errorMessage(err) {
  if (!err?.response) return "Cannot reach the server. Is the backend running?";
  const data = err.response.data;
  if (!data || typeof data !== "object") return "Something went wrong. Please try again.";
  return (
    firstFieldError(data.errors) ||
    data.message ||
    data.detail ||
    firstFieldError(data) ||
    "Something went wrong. Please try again."
  );
}

// The backend paginates lists (10 per page). This follows `next` until every item is loaded.
// `get(url, params)` must resolve to the response body.
export async function fetchAllPages(get, url, params = {}, maxPages = 50) {
  const items = [];
  for (let page = 1; page <= maxPages; page += 1) {
    const data = await get(url, { ...params, page });
    if (Array.isArray(data)) return data;
    items.push(...(data?.results ?? []));
    if (!data?.next) break;
  }
  return items;
}