import {JSDOM} from 'jsdom';
import React from 'react';
import test,{afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {previewCues,ChangePreview,ChangeEditor,VersionImpact} from '../src/ReviewTools';
const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'http://localhost'});
Object.assign(globalThis,{window:dom.window,document:dom.window.document,HTMLElement:dom.window.HTMLElement});
Object.defineProperty(globalThis,'navigator',{value:dom.window.navigator,configurable:true});
const {render,fireEvent,cleanup}=require('@testing-library/react');
afterEach(cleanup);
const asset:any={id:'a',name:'Spanish subtitles',kind:'SUBTITLE',master_offset:10,revision:1,cues:[{id:'one',start:1,end:4,text:'4 passengers'},{id:'two',start:5,end:6,text:'Remove me'}]};
const changes:any=[{asset_id:'a',cue_id:'one',operation:'REPLACE',base_hash:'hash',replacement:{id:'one',start:1,end:4,text:'14 passengers'}},{asset_id:'a',cue_id:'two',operation:'DELETE',base_hash:'hash',replacement:null},{asset_id:'a',cue_id:'three',operation:'INSERT',base_hash:'hash',replacement:{id:'three',start:7,end:8,text:'[Bell rings]'}}];
const proposal:any={id:'p',status:'PROPOSED',changes,snapshots:[],rationale:'Keep the number correct.'};
test('preview handles replacement, insertion and deletion without mutating source',()=>{
 const before=JSON.stringify(asset);assert.deepEqual(previewCues(asset,changes).map(c=>c.text),['14 passengers','[Bell rings]']);assert.equal(JSON.stringify(asset),before);
});
test('before and after play on the original timeline including a derivative offset',()=>{
 const ui=render(<ChangePreview assets={[asset]} proposal={proposal} videoUrl="/film.mp4"/>);const video=ui.container.querySelector('video')!;
 fireEvent.timeUpdate(video,{target:{currentTime:12}});assert.ok(ui.getByText('4 passengers'));
 fireEvent.click(ui.getByRole('button',{name:'After',exact:true}));assert.ok(ui.getByText('14 passengers'));assert.equal(ui.queryByText('4 passengers'),null);
 fireEvent.timeUpdate(video,{target:{currentTime:17.5}});assert.ok(ui.getByText('[Bell rings]'));
 fireEvent.click(ui.getByRole('button',{name:'Before',exact:true}));assert.equal(ui.queryByText('[Bell rings]'),null);
});
test('applied preview uses retained pre-change assets, not the current edited cues',()=>{
 const ui=render(<ChangePreview assets={[{...asset,cues:previewCues(asset,changes)}]} proposal={{...proposal,status:'APPLIED',preview_assets:[asset]}} videoUrl="/film.mp4"/>);
 fireEvent.timeUpdate(ui.container.querySelector('video')!,{target:{currentTime:12}});assert.ok(ui.getByText('4 passengers'));
});
test('normal editor preserves identity and hashes while changing caption text',async()=>{
 let saved:any;const ui=render(<ChangeEditor assets={[asset]} proposal={{...proposal,changes:[changes[0]]}} busy={false} onCancel={()=>{}} onSave={async p=>{saved=p;}}/>);
 fireEvent.change(ui.getByLabelText('Caption text'),{target:{value:'There are 14 passengers.'}});
 fireEvent.submit(ui.container.querySelector('form')!);
 await new Promise(r=>setTimeout(r,0));assert.equal(saved.changes[0].cue_id,'one');assert.equal(saved.changes[0].base_hash,'hash');assert.equal(saved.changes[0].replacement.text,'There are 14 passengers.');
});
test('editor rejects an end time before start',async()=>{
 let saved=false;const ui=render(<ChangeEditor assets={[asset]} proposal={{...proposal,changes:[{...changes[0],replacement:{...changes[0].replacement,end:.5}}]}} busy={false} onCancel={()=>{}} onSave={async()=>{saved=true;}}/>);
 fireEvent.submit(ui.container.querySelector('form')!);assert.ok(ui.getByRole('alert'));assert.equal(saved,false);
});
test('impact view reports only actual proposal changes and known parent',()=>{
 const child={...asset,id:'b',name:'Trailer',parent_id:'a'};const ui=render(<VersionImpact assets={[asset,child]} findings={[{asset_id:'b'}]} changes={[changes[0]]}/>);
 assert.ok(ui.getByText('From Spanish subtitles'));assert.ok(ui.getByText('1 to review'));assert.equal(ui.getAllByText('1 proposed change').length,1);
});
