(() => {
  'use strict';
  let recording = false;
  const fields = new WeakMap();
  const pending = new Set();
  const secretField = /pass(word|code)?|pwd|one.?time|otp|verif|security.?code|card.?number|cc-number|cc-csc|cvv|cvc|密码|验证码|安全码|银行卡|口令|api.?key|secret|token/iu;

  async function refreshSettings() {
    try {
      const result = await chrome.runtime.sendMessage({type: 'can-record'});
      recording = result?.allowed === true;
      if (!recording) {
        for (const item of pending) { clearTimeout(item.timer); clearTimeout(item.deadline); }
        pending.clear();
      }
    } catch { recording = false; }
  }
  chrome.runtime.onMessage.addListener(message => {
    if (message?.type === 'settings-changed') void refreshSettings();
  });
  void refreshSettings();

  function inputFor(target) {
    if (!(target instanceof Element)) return null;
    const el = target.closest('textarea,input,[contenteditable="true"],[contenteditable="plaintext-only"],[role="textbox"]');
    if (!el || el.disabled || el.readOnly || el.getAttribute('aria-hidden') === 'true') return null;
    const tag = el.tagName.toLowerCase();
    if (tag === 'input' && !['text', 'search', 'url'].includes(el.type)) return null;
    if (tag !== 'input' && tag !== 'textarea' && !el.isContentEditable) return null;
    if (tag === 'input' && el.maxLength > 0 && el.maxLength <= 8) return null;
    const labels = el.labels ? Array.from(el.labels).map(label => label.textContent || '').join(' ') : '';
    const labelledBy = (el.getAttribute('aria-labelledby') || '').split(/\s+/)
      .map(id => document.getElementById(id)?.textContent || '').join(' ');
    const metadata = [el.id, el.getAttribute('name'), el.getAttribute('type'),
      el.getAttribute('autocomplete'), el.getAttribute('placeholder'),
      el.getAttribute('aria-label'), labels, labelledBy].filter(Boolean).join(' ');
    if (secretField.test(metadata) || el.closest('[data-private], [data-sensitive]')) return null;
    return el;
  }
  function textOf(el) {
    return (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') ? el.value : el.innerText;
  }
  function warn() {
    if (!document.body || document.getElementById('clipvault-save-warning')) return;
    const notice = document.createElement('div');
    notice.id = 'clipvault-save-warning';
    notice.setAttribute('role', 'status');
    notice.textContent = 'ClipVault：草稿未能保存，请检查浏览器扩展。';
    Object.assign(notice.style, {position:'fixed', right:'16px', bottom:'16px', zIndex:'2147483647',
      padding:'10px 14px', borderRadius:'8px', color:'#fff', background:'#a4262c',
      font:'14px sans-serif', boxShadow:'0 4px 18px #0004'});
    document.body.append(notice);
    setTimeout(() => notice.remove(), 7000);
  }
  function flush(item) {
    clearTimeout(item.timer); clearTimeout(item.deadline);
    item.timer = item.deadline = null;
    pending.delete(item);
    if (!recording || !item.latest || item.latest === item.lastSent) return;
    const text = item.latest;
    item.lastSent = text;
    item.lastSentAt = Date.now();
    item.chain = item.chain.catch(() => {}).then(async () => {
      try {
        const response = await chrome.runtime.sendMessage({type:'capture', id:item.id, text});
        if (!response?.ok && response?.error === 'storage') { item.lastSent = ''; warn(); }
      } catch { item.lastSent = ''; warn(); }
    });
  }
  function record(target) {
    if (!recording) return;
    const el = inputFor(target);
    if (!el) return;
    const text = textOf(el);
    if (typeof text !== 'string' || !text.trim()) return;
    if (text.length > 100000) { warn(); return; }
    let item = fields.get(el);
    if (!item) {
      item = {id:crypto.randomUUID(), latest:'', lastSent:'', lastSentAt:0,
        timer:null, deadline:null, chain:Promise.resolve()};
      fields.set(el, item);
    }
    item.latest = text;
    pending.add(item);
    if (!item.lastSentAt || Date.now() - item.lastSentAt >= 2500) {
      flush(item);
      return;
    }
    clearTimeout(item.timer);
    item.timer = setTimeout(() => flush(item), 550);
    if (!item.deadline) item.deadline = setTimeout(() => flush(item), 2000);
  }
  document.addEventListener('input', event => {
    if (event.isTrusted && !event.isComposing) record(event.target);
  }, true);
  document.addEventListener('compositionend', event => {
    if (event.isTrusted) setTimeout(() => record(event.target), 0);
  }, true);
  document.addEventListener('focusout', event => {
    if (!event.isTrusted || !recording) return;
    const el = inputFor(event.target);
    const item = el && fields.get(el);
    if (item && pending.has(item)) flush(item);
  }, true);
  const flushPending = () => { for (const item of [...pending]) flush(item); };
  window.addEventListener('pagehide', flushPending);
  document.addEventListener('visibilitychange', () => { if (document.hidden) flushPending(); });
})();
