import test from 'node:test';
import assert from 'node:assert/strict';
import {DEFAULT_CONFIG, allowed, originOf, pagePath, prune, saveCapture, toWire, validCapture} from '../../browser-extension/logic.mjs';
const first='7b4b12fe-5d20-4e95-bbb9-beb61cbc1a80';
const second='c0c2111a-8bb2-48da-a29c-5d1e005c1ca9';
const now=Date.parse('2026-11-06T12:00:00Z');

test('only enabled, allowed non-incognito origins can record',()=>{
  assert.equal(allowed(DEFAULT_CONFIG,'https://chatgpt.com/c/abc?secret=yes'),true);
  assert.equal(allowed(DEFAULT_CONFIG,'https://evil.example'),false);
  assert.equal(allowed(DEFAULT_CONFIG,'https://chatgpt.com',true),false);
  assert.equal(allowed({...DEFAULT_CONFIG,enabled:false},'https://chatgpt.com'),false);
  assert.equal(originOf('file:///private'),null);
  assert.equal(originOf('https://name:secret@example.com'),null);
  assert.equal(pagePath('https://example.com/p?token=secret#frag'),'/p');
});

test('snapshots keep multiline Chinese, avoid duplicates and archive before shortening',()=>{
  const text='这是一段很长很长的中文草稿，断网之后希望仍然可以恢复，第二行也要保留。\n第二行';
  assert.equal(validCapture(first,text),true);
  assert.equal(validCapture(first,'   '),false);
  assert.equal(validCapture(first,'x\u0000y'),false);
  assert.equal(validCapture(first,'\ud800'),false);
  let result=saveCapture([], {id:first,text,origin:'https://chatgpt.com',path:'/c/a'},now,()=>second);
  assert.equal(result.items.length,1);
  assert.equal(result.items[0].revision,1);
  assert.equal(result.items[0].text,text);
  const duplicate=saveCapture(result.items,{id:first,text,origin:'https://chatgpt.com',path:'/c/a'},now+6000,()=>second);
  assert.equal(duplicate.changed,false);
  result=saveCapture(result.items,{id:first,text:'新内容',origin:'https://chatgpt.com',path:'/c/a'},now+1000,()=>second);
  assert.equal(result.items.length,2);
  assert.equal(result.items.find(x=>x.id===second).text,text);
  assert.equal(result.items.find(x=>x.id===second).archived,true);
  assert.equal(result.items.find(x=>x.id===first).revision,2);
  assert.deepEqual(Object.keys(toWire(result.items[0])).sort(), ['created_at','id','origin','path','revision','text','updated_at']);
});

test('retention removes records older than 30 days and caps history',()=>{
  const old = {updated_at:new Date(now-31*86400000).toISOString(),text:'old'};
  const fresh = {updated_at:new Date(now).toISOString(),text:'new'};
  assert.deepEqual(prune([old,fresh],now),[fresh]);
  assert.equal(prune(Array.from({length:550},()=>fresh),now).length,500);
});
