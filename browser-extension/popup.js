import {DEFAULT_CONFIG, originOf} from './logic.mjs';
const $ = id => document.getElementById(id);
let currentOrigin = null;
let isIncognito = false;
let allDrafts = [];
let notifyTimer;
function toast(message) {
  $('toast').textContent = message; $('toast').style.display = 'block';
  clearTimeout(notifyTimer); notifyTimer = setTimeout(() => { $('toast').style.display = 'none'; }, 2800);
}
async function send(message) {
  try { return await chrome.runtime.sendMessage(message); } catch { toast('扩展暂时不可用，请刷新后重试'); return {ok:false}; }
}
function dayOf(timestamp) {
  const d = new Date(timestamp);
  if (Number.isNaN(d.getTime())) return '未知日期';
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}
function timeOf(timestamp) {
  const d = new Date(timestamp);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'});
}
function renderDrafts() {
  const root = $('drafts'); root.replaceChildren();
  const query = $('search').value.trim().toLocaleLowerCase();
  const rows = [...allDrafts].sort((a,b) => b.updated_at.localeCompare(a.updated_at))
    .filter(row => !query || (row.text + ' ' + row.origin).toLocaleLowerCase().includes(query));
  $('empty').hidden = rows.length > 0;
  $('empty').textContent = query ? '没有找到匹配的草稿。' : '暂时没有草稿。在已允许的网站输入文字后会自动保存。';
  let lastDay = null;
  for (const row of rows) {
    const day = dayOf(row.updated_at);
    if (day !== lastDay) { const heading=document.createElement('div'); heading.className='day'; heading.textContent=day; root.append(heading); lastDay=day; }
    const card=document.createElement('details'); card.className='draft';
    const summary=document.createElement('summary');
    const meta=document.createElement('div'); meta.className='meta';
    let hostname = row.origin; try { hostname = new URL(row.origin).hostname; } catch {}
    meta.textContent = `${timeOf(row.updated_at)} · ${hostname}${row.archived ? ' · 历史版本' : ''}`;
    const snippet=document.createElement('div'); snippet.className='snippet'; snippet.textContent=row.text.slice(0,180);
    summary.append(meta,snippet); card.append(summary);
    const full=document.createElement('pre'); full.className='full'; full.textContent=row.text; card.append(full);
    const actions=document.createElement('div'); actions.className='actions';
    const copy=document.createElement('button'); copy.type='button'; copy.className='primary'; copy.textContent='复制';
    copy.addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(row.text); toast('已复制，回到输入框粘贴即可'); }
      catch { toast('复制失败，请展开后手动选择文字'); }
    });
    const remove=document.createElement('button'); remove.type='button'; remove.textContent='删除';
    remove.addEventListener('click', async () => { const result=await send({type:'remove-draft',id:row.id}); if(result?.ok) toast('已删除浏览器中的副本'); });
    actions.append(copy,remove); card.append(actions); root.append(card);
  }
}
async function render() {
  const data=await chrome.storage.local.get(['config','drafts','pairingToken','syncError']);
  const config=data.config || {enabled:true,sites:[...DEFAULT_CONFIG.sites]};
  allDrafts=Array.isArray(data.drafts)?data.drafts:[];
  $('enabled').checked=!!config.enabled;
  $('site-name').textContent=isIncognito?'隐身窗口默认不记录':(currentOrigin || '此页面不支持草稿备份');
  $('site-toggle').disabled=!currentOrigin || isIncognito;
  const allowed=currentOrigin && config.sites.includes(currentOrigin);
  $('site-toggle').textContent=allowed?'停止记录本站':'允许本站';
  $('site-toggle').dataset.enabled=allowed?'yes':'no';
  const unsynced=allDrafts.filter(x=>x.revision>(x.synced_revision||0)).length;
  $('sync-status').textContent=data.pairingToken ? (data.syncError || (unsynced ? `待同步 ${unsynced} 条` : '已配对')) : '未配对';
  $('sync').disabled=!data.pairingToken;
  $('unpair').disabled=!data.pairingToken;
  renderDrafts();
}
$('enabled').addEventListener('change', async e => { await send({type:'set-enabled',enabled:e.target.checked}); await render(); });
$('site-toggle').addEventListener('click', async () => {
  if (!currentOrigin || isIncognito) return;
  const enabled=$('site-toggle').dataset.enabled!=='yes';
  const result=await send({type:'toggle-site',origin:currentOrigin,enabled});
  if(result?.ok) toast(enabled?'已允许本站，输入文字后自动保存':'已停止记录本站');
  await render();
});
$('search').addEventListener('input',renderDrafts);
$('clear').addEventListener('click', async () => {
  if (allDrafts.length && confirm('清空浏览器扩展里的所有草稿？ClipVault 中已同步的副本不会删除。')) {
    await send({type:'clear-drafts'}); toast('浏览器中的草稿已清空');
  }
});
$('pair').addEventListener('click', async () => {
  const token=$('token').value.trim();
  if (!/^[A-Za-z0-9_-]{40,64}$/.test(token)) { $('pair-message').textContent='配对码格式不正确，请重新从 ClipVault 复制。'; return; }
  $('pair').disabled=true; $('pair-message').textContent='正在连接本机 ClipVault…';
  try {
    const response=await fetch('http://127.0.0.1:47963/v1/status',{headers:{Authorization:`Bearer ${token}`},signal:AbortSignal.timeout(7000)});
    if(!response.ok) throw new Error('pair');
    const result=await send({type:'set-token',token});
    if(!result?.ok) throw new Error('save');
    $('token').value=''; $('pair-message').textContent='连接成功，草稿会自动同步。';
    await render();
  } catch { $('pair-message').textContent='连接失败：请确认 ClipVault 已开启浏览器同步，并允许浏览器访问本机。'; }
  finally { $('pair').disabled=false; }
});
$('sync').addEventListener('click', async () => { await send({type:'sync-now'}); toast('正在尝试同步'); });
$('unpair').addEventListener('click', async () => { await send({type:'set-token',token:''}); toast('已解除配对，本地备份继续'); });
chrome.storage.onChanged.addListener((_changes,area) => { if(area==='local') void render(); });
try {
  const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
  isIncognito=!!tab?.incognito; currentOrigin=originOf(tab?.url || '');
} catch {}
await render();
