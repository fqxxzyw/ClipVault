import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
import {webcrypto} from 'node:crypto';
const source=fs.readFileSync(new URL('../../browser-extension/content.js',import.meta.url),'utf8');
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));

function harness(allowed=true){
  const events={},windowEvents={},messages=[];
  let messageHandler;
  class Element {
    constructor({tag='TEXTAREA',value='',type='text',attrs={},editable=false,maxLength=-1}={}) {
      this.tagName=tag;this.value=value;this.type=type;this.attrs=attrs;this.id=attrs.id||'';
      this.isContentEditable=editable;this.maxLength=maxLength;this.disabled=false;this.readOnly=false;this.labels=[];
      this.innerText=value;
    }
    closest(selector){ return selector.includes('data-private') ? null : this; }
    getAttribute(key){return this.attrs[key]??null;}
  }
  const document={addEventListener:(name,handler)=>{events[name]=handler;},body:{append(){}},getElementById:()=>null};
  const window={addEventListener:(name,handler)=>{windowEvents[name]=handler;}};
  const chrome={runtime:{sendMessage:async message=>{
    messages.push(message); return message.type==='can-record'?{allowed}:{ok:true};
  },onMessage:{addListener:handler=>{messageHandler=handler;}}}};
  const sandbox={Element,document,window,chrome,crypto:webcrypto,setTimeout,clearTimeout,Date,Promise};
  vm.runInNewContext(source,sandbox);
  return {events,windowEvents,messages,Element,setAllowed:value=>{allowed=value;messageHandler({type:'settings-changed'});}};
}

test('captures user text and flushes pending content on page hide',async()=>{
  const h=harness();await wait(5);
  const el=new h.Element({value:'你好，第一段长草稿'});
  h.events.input({isTrusted:true,isComposing:false,target:el});
  await wait(10);
  assert.equal(h.messages.filter(x=>x.type==='capture')[0].text,'你好，第一段长草稿');
  el.value='你好，第一段长草稿\n接着输入的文字';
  h.events.input({isTrusted:true,isComposing:false,target:el});
  h.windowEvents.pagehide();await wait(10);
  assert.equal(h.messages.filter(x=>x.type==='capture').at(-1).text,el.value);
});

test('does not save password, OTP, payment fields, composition-in-progress or disabled sites',async()=>{
  const h=harness();await wait(5);
  for(const el of [new h.Element({tag:'INPUT',type:'password',value:'secret'}),
    new h.Element({tag:'INPUT',value:'123456',attrs:{'autocomplete':'one-time-code'}}),
    new h.Element({value:'4111',attrs:{'aria-label':'银行卡号'}})]) {
    h.events.input({isTrusted:true,isComposing:false,target:el});
  }
  const normal=new h.Element({value:'拼音尚未完成'});
  h.events.input({isTrusted:true,isComposing:true,target:normal});
  await wait(10);assert.equal(h.messages.filter(x=>x.type==='capture').length,0);
  h.setAllowed(false);await wait(10);
  h.events.input({isTrusted:true,isComposing:false,target:normal});
  await wait(10);assert.equal(h.messages.filter(x=>x.type==='capture').length,0);
});
