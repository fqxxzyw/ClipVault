export const DEFAULT_CONFIG = Object.freeze({
  enabled: true,
  sites: ["https://chatgpt.com", "https://chat.openai.com"],
});
export const MAX_TEXT = 100000;
export const MAX_ITEMS = 500;
export const MAX_BYTES = 5_000_000;
const KEEP_MS = 30 * 24 * 60 * 60 * 1000;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function originOf(value) {
  try {
    const u = new URL(value);
    return ["https:", "http:"].includes(u.protocol) && !u.username && !u.password ? u.origin : null;
  } catch { return null; }
}
export function pagePath(value) {
  try { return (new URL(value).pathname || "/").slice(0, 512); } catch { return "/"; }
}
export function allowed(config, url, incognito = false) {
  const origin = originOf(url);
  return !incognito && !!origin && config?.enabled === true && Array.isArray(config.sites)
    && config.sites.includes(origin);
}
export function validCapture(id, text) {
  return typeof id === "string" && UUID.test(id) && typeof text === "string"
    && text.length <= MAX_TEXT && text.trim().length > 0 && !text.includes("\0")
    && !/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(text);
}
export function saveCapture(items, {id, text, origin, path}, now, newId) {
  const copy = items.map(item => ({...item}));
  let item = copy.find(row => row.id === id);
  if (item?.text === text) return {items: copy, changed: false};
  const stamp = new Date(now).toISOString();
  if (!item) {
    item = {id, origin, path, text, created_at: stamp, updated_at: stamp,
      revision: 1, synced_revision: 0, last_archive: now, archived: false};
    copy.push(item);
  } else {
    const sinceArchive = now - (item.last_archive || Date.parse(item.created_at));
    const shortening = text.length < item.text.length && item.text.length >= 32;
    const drasticallyShorter = text.length * 2 < item.text.length;
    if ((shortening && (sinceArchive >= 5000 || drasticallyShorter))
        || (item.text.length >= 32 && sinceArchive >= 30000)) {
      copy.push({...item, id: newId(), revision: 1, synced_revision: 0, archived: true,
        last_archive: now});
      item.last_archive = now;
    }
    Object.assign(item, {text, origin, path, updated_at: stamp, revision: item.revision + 1});
  }
  return {items: prune(copy, now), changed: true};
}
export function prune(items, now) {
  const rows = items.filter(item => Number.isFinite(Date.parse(item.updated_at))
    && now - Date.parse(item.updated_at) <= KEEP_MS)
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at)).slice(0, MAX_ITEMS);
  const encoder = new TextEncoder();
  while (rows.length > 1 && encoder.encode(JSON.stringify(rows)).length > MAX_BYTES) rows.pop();
  return rows;
}
export function toWire(item) {
  return {id: item.id, origin: item.origin, path: item.path, text: item.text,
    created_at: item.created_at, updated_at: item.updated_at, revision: item.revision};
}
