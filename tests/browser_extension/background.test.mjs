import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {webcrypto} from 'node:crypto';
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const waitFor = async fn => { for (let i=0;i<100;i++){if(fn()) return; await wait(10);} throw Error('condition timed out'); };

test('background stores locally, enforces scope and retries desktop sync without losing text',async()=>{
  let data={},onMessage,alarmHandler,offline=true;
  const sent=[],badges=[];
  const clone = x => structuredClone(x);
  const extId='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';
  if (!globalThis.crypto) Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true});
  globalThis.chrome={
    storage:{local:{setAccessLevel:async()=>{},get:async keys=>{
      if(typeof keys==='string') return {[keys]:clone(data[keys])};
      const out={};for(const key of keys) if(key in data) out[key]=clone(data[key]);return out;
    },set:async values=>{data={...data,...clone(values)};}}},
    runtime:{id:extId,getURL:path=>`chrome-extension://${extId}${path}`,
      onMessage:{addListener:f=>{onMessage=f;}},onStartup:{addListener:()=>{}}},
    tabs:{query:async()=>[],sendMessage:async()=>{}},
    alarms:{create:()=>{},onAlarm:{addListener:f=>{alarmHandler=f;}}},
    action:{setBadgeText:async x=>{badges.push(x.text);},setBadgeBackgroundColor:async()=>{}},
  };
  globalThis.fetch=async(url,options)=>{
    if(offline) throw Error('offline');
    assert.equal(url,'http://127.0.0.1:47963/v1/drafts');
    assert.match(options.headers.Authorization,/^Bearer /);
    sent.push(JSON.parse(options.body));return {ok:true};
  };
  const logic = new URL('../../browser-extension/logic.mjs',import.meta.url).href;
  let source=fs.readFileSync(new URL('../../browser-extension/background.js',import.meta.url),'utf8')
    .replace("'./logic.mjs'",JSON.stringify(logic));
  await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
  const send=(message,sender)=>new Promise(resolve=>onMessage(message,sender,resolve));
  const page={id:extId,url:'https://chatgpt.com/c/abc?token=never-save',tab:{id:1,incognito:false}};
  const popup={id:extId,url:`chrome-extension://${extId}/popup.html`};
  const id='7b4b12fe-5d20-4e95-bbb9-beb61cbc1a80';
  assert.equal((await send({type:'can-record'},page)).allowed,true);
  assert.equal((await send({type:'capture',id,text:'中文草稿'},page)).ok,true);
  assert.equal(data.drafts[0].text,'中文草稿');
  assert.equal(data.drafts[0].path,'/c/abc');
  assert.equal((await send({type:'capture',id,text:'secret'}, {...page,url:'https://evil.example'})).ok,false);
  assert.equal((await send({type:'capture',id,text:'secret'}, {...page,tab:{id:1,incognito:true}})).ok,false);
  assert.equal((await send({type:'set-token',token:'A'.repeat(43)},page)).ok,false);
  assert.equal((await send({type:'sync-now'},{...popup,tab:{id:3}})).ok,true);
  assert.equal((await send({type:'set-token',token:'A'.repeat(43)},popup)).ok,true);
  await waitFor(()=>data.syncError==='等待 ClipVault 同步');
  assert.equal(data.drafts[0].text,'中文草稿');
  assert.equal(data.drafts[0].synced_revision,0);
  offline=false;
  await send({type:'sync-now'},popup);
  await waitFor(()=>data.drafts[0].synced_revision===1);
  assert.equal(sent[0].text,'中文草稿');
  assert.equal(JSON.stringify(sent[0]).includes('never-save'),false);
  await send({type:'set-enabled',enabled:false},popup);
  assert.equal((await send({type:'capture',id,text:'disabled'},page)).ok,false);
  assert.equal(data.drafts[0].text,'中文草稿');
  assert.equal(typeof alarmHandler,'function');
});
