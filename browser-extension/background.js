import {DEFAULT_CONFIG, allowed, originOf, pagePath, saveCapture, toWire, validCapture} from './logic.mjs';

const API = 'http://127.0.0.1:47963';
let queue = Promise.resolve();
let syncing = false;
const restricted = chrome.storage.local.setAccessLevel({accessLevel: 'TRUSTED_CONTEXTS'}).catch(() => {});
function mutate(fn) {
  const task = queue.then(async () => { await restricted; return fn(); });
  queue = task.catch(() => {});
  return task;
}
async function state() {
  await restricted;
  const stored = await chrome.storage.local.get(['config', 'drafts', 'pairingToken', 'syncError']);
  return {config: stored.config || {enabled: true, sites: [...DEFAULT_CONFIG.sites]},
    drafts: Array.isArray(stored.drafts) ? stored.drafts : [],
    pairingToken: stored.pairingToken || '', syncError: stored.syncError || ''};
}
function popupSender(sender) {
  return sender.id === chrome.runtime.id && typeof sender.url === 'string'
    && sender.url.startsWith(chrome.runtime.getURL('/'));
}
function contentSender(sender) {
  return sender.id === chrome.runtime.id && !!sender.tab && typeof sender.url === 'string';
}
async function notifySettings() {
  const tabs = await chrome.tabs.query({});
  await Promise.all(tabs.filter(tab => tab.id !== undefined).map(tab =>
    chrome.tabs.sendMessage(tab.id, {type: 'settings-changed'}).catch(() => {})));
}
async function capture(message, sender) {
  if (!contentSender(sender) || !validCapture(message.id, message.text)) return {ok: false};
  return mutate(async () => {
    const stored = await state();
    if (!allowed(stored.config, sender.url, sender.tab.incognito)) return {ok: false};
    const result = saveCapture(stored.drafts,
      {id: message.id, text: message.text, origin: originOf(sender.url), path: pagePath(sender.url)},
      Date.now(), () => crypto.randomUUID());
    if (result.changed) await chrome.storage.local.set({drafts: result.items});
    chrome.action.setBadgeText({text: ''}).catch(() => {});
    return {ok: true, changed: result.changed};
  }).then(result => { if (result.ok && result.changed) void syncDrafts(); return result; })
    .catch(() => {
      chrome.action.setBadgeBackgroundColor({color: '#c42b1c'}).catch(() => {});
      chrome.action.setBadgeText({text: '!'}).catch(() => {});
      return {ok: false, error: 'storage'};
    });
}
async function syncDrafts() {
  if (syncing) return;
  syncing = true;
  try {
    let snapshot = await state();
    if (!snapshot.pairingToken) return;
    const token = snapshot.pairingToken;
    const pending = snapshot.drafts.filter(row => row.revision > (row.synced_revision || 0)).slice(-50);
    for (const item of pending) {
      let response;
      try {
        response = await fetch(`${API}/v1/drafts`, {method: 'POST',
          headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`},
          body: JSON.stringify(toWire(item)), signal: AbortSignal.timeout(7000)});
      } catch { response = null; }
      if (!response?.ok) {
        await mutate(() => chrome.storage.local.set({syncError: '等待 ClipVault 同步'}));
        return;
      }
      await mutate(async () => {
        const current = await state();
        const live = current.drafts.find(row => row.id === item.id);
        if (live) live.synced_revision = Math.max(live.synced_revision || 0, item.revision);
        await chrome.storage.local.set({drafts: current.drafts, syncError: ''});
      });
      snapshot = await state();
      if (snapshot.pairingToken !== token) return;
    }
  } finally { syncing = false; }
}
async function handle(message, sender) {
  if (message?.type === 'can-record' && contentSender(sender)) {
    const {config} = await state();
    return {allowed: allowed(config, sender.url, sender.tab.incognito)};
  }
  if (message?.type === 'capture') return capture(message, sender);
  if (!popupSender(sender)) return {ok: false};
  if (message.type === 'set-enabled') {
    const result = await mutate(async () => {
      const {config} = await state();
      config.enabled = message.enabled === true;
      await chrome.storage.local.set({config});
      return {ok: true};
    });
    void notifySettings(); return result;
  }
  if (message.type === 'toggle-site') {
    const origin = originOf(message.origin);
    if (!origin || origin !== message.origin) return {ok: false};
    const result = await mutate(async () => {
      const {config} = await state();
      const sites = new Set(config.sites);
      if (message.enabled === true) sites.add(origin); else sites.delete(origin);
      config.sites = [...sites];
      await chrome.storage.local.set({config});
      return {ok: true};
    });
    void notifySettings(); return result;
  }
  if (message.type === 'remove-draft' || message.type === 'clear-drafts') {
    return mutate(async () => {
      const {drafts} = await state();
      await chrome.storage.local.set({drafts: message.type === 'clear-drafts' ? [] : drafts.filter(x => x.id !== message.id)});
      return {ok: true};
    });
  }
  if (message.type === 'set-token') {
    if (message.token && !/^[A-Za-z0-9_-]{40,64}$/.test(message.token)) return {ok: false};
    await mutate(() => chrome.storage.local.set({pairingToken: message.token || '', syncError: ''}));
    void syncDrafts(); return {ok: true};
  }
  if (message.type === 'sync-now') { void syncDrafts(); return {ok: true}; }
  return {ok: false};
}
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  handle(message, sender).then(respond).catch(() => respond({ok: false}));
  return true;
});
chrome.alarms.create('draft-sync', {periodInMinutes: 1});
chrome.alarms.onAlarm.addListener(alarm => { if (alarm.name === 'draft-sync') void syncDrafts(); });
chrome.runtime.onStartup.addListener(() => { void syncDrafts(); });
