// Capture actual hosted UI states. No response interception or simulated service data.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs');
let browser,page;
(async()=>{
 const url=process.env.STORYPARITY_URL, phase=process.argv[2];
 const mobileChecks=process.env.STORYPARITY_MOBILE_CHECK==='1';
 browser=await chromium.launch({headless:true,channel:'chrome'});
 page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1,recordVideo:mobileChecks?undefined:{dir:'runtime/demo-capture/recordings',size:{width:1440,height:1000}}});
 const recordingStarted=Date.now(), clips=[];
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route(url+'/**',route=>route.continue({headers:{...route.request().headers(),'X-Serverless-Authorization':'Bearer '+process.env.STORYPARITY_IDENTITY}}));
 fs.mkdirSync('runtime/demo-capture',{recursive:true});
 await page.goto(url);
 if(phase==='before'){await page.screenshot({path:'runtime/demo-capture/00-welcome.png'});}
 await page.getByLabel('Access code').fill(process.env.STORYPARITY_REVIEWER_TOKEN);
 await page.getByRole('button',{name:'Continue'}).click();
 const projectsResponse=await page.request.get(url+'/api/projects',{headers:{'X-Serverless-Authorization':'Bearer '+process.env.STORYPARITY_IDENTITY,'Authorization':'Bearer '+process.env.STORYPARITY_REVIEWER_TOKEN}});
 const projects=await projectsResponse.json();
 const index=projects.findIndex(p=>p.id===process.env.STORYPARITY_CAPTURE_PROJECT);
 if(index<0)throw new Error('Capture project not found');
 await page.locator('nav button').nth(index).click();
 await page.getByRole('heading',{name:'Your versions'}).waitFor();
 if(phase==='before') await page.waitForFunction(()=>{const v=document.querySelector('video');return v&&v.readyState>=2;},undefined,{timeout:90000});
 fs.mkdirSync('runtime/demo-capture',{recursive:true});
 async function snap(name){await page.screenshot({path:'runtime/demo-capture/'+name+'.png',fullPage:false});clips.push({name,start:(Date.now()-recordingStarted)/1000});await page.waitForTimeout(6000);}
 if(phase==='before'){
   await page.locator('video').evaluate(v=>{v.currentTime=1;v.play();});await snap('01-sources');await page.locator('video').evaluate(v=>v.pause());
   if(mobileChecks){
   await page.setViewportSize({width:390,height:844});
   if(await page.evaluate(()=>document.body.scrollWidth)>390)throw new Error('Sources mobile overflow');
   await page.screenshot({path:'runtime/demo-capture/mobile-sources.png',fullPage:true});
   await page.setViewportSize({width:1440,height:1000});
   }
   await page.getByRole('button',{name:'Story notes',exact:true}).click();await snap('02-spec');
   await page.getByRole('button',{name:'Review',exact:true}).click();
   await page.locator('.finding').filter({hasText:'Spanish subtitles.json'}).filter({hasText:'Expected 14; observed 4'}).getByRole('button',{name:'Review evidence'}).click();
   await page.locator('.evidence-player').scrollIntoViewIfNeeded();
   await page.locator('video').evaluate(v=>{v.currentTime=9;v.play();});
   await page.waitForFunction(()=>document.querySelector('video')?.readyState>=2,undefined,{timeout:20000});
   await snap('03-findings');
   await page.locator('.findings-grid').scrollIntoViewIfNeeded();await snap('04-defects');
 }else if(phase==='proposal'){
   await page.getByRole('button',{name:'Changes',exact:true}).click();
   const preview=page.locator('.change-preview').first();await preview.waitFor({state:'visible',timeout:90000});await preview.getByLabel('Preview track').selectOption({label:'Spanish subtitles.json'});await preview.scrollIntoViewIfNeeded();
   await page.waitForFunction(()=>{const v=document.querySelector('.change-preview video');return v&&v.readyState>=2;},undefined,{timeout:90000});
   await preview.locator('video').evaluate(async v=>{v.currentTime=9;await v.play();await new Promise(resolve=>v.requestVideoFrameCallback(resolve));});
   await preview.getByRole('button',{name:'After',exact:true}).click();
   await snap('05-proposal');
   await page.getByRole('button',{name:'Edit changes',exact:true}).first().click();
   const editor=page.locator('.change-editor').first();await editor.scrollIntoViewIfNeeded();
   const text=editor.getByLabel('Caption text').first();const previous=await text.inputValue();
   await text.fill(previous+' ');if(await text.inputValue()!==previous+' ')throw new Error('Caption editor did not update');
   await snap('05b-editor');await editor.getByRole('button',{name:'Cancel',exact:true}).click();
   await preview.scrollIntoViewIfNeeded();
 }else if(phase==='after'){
   await page.getByRole('button',{name:'Changes',exact:true}).click();
   const appliedPreview=page.locator('.change-preview').first();
   await appliedPreview.getByLabel('Preview track').selectOption({label:'Spanish subtitles.json'});
   await appliedPreview.getByRole('button',{name:'After',exact:true}).click();
   await appliedPreview.scrollIntoViewIfNeeded();
   await page.waitForFunction(()=>{const v=document.querySelector('.change-preview video');return v&&v.readyState>=2;},undefined,{timeout:90000});
   await appliedPreview.locator('video').evaluate(async v=>{v.currentTime=9;await v.play();await new Promise(resolve=>v.requestVideoFrameCallback(resolve));});
   await snap('05-proposal');
   await page.getByRole('button',{name:'Review',exact:true}).click();await snap('06-verified');
   await page.getByRole('button',{name:'History',exact:true}).click();
   await snap('07-evidence');
 }else{
   await page.getByRole('button',{name:'Review',exact:true}).click();await snap('08-rollback');
 }
 if(mobileChecks){
 await page.setViewportSize({width:390,height:844});
 const width=await page.evaluate(()=>document.body.scrollWidth);
 if(width>390)throw new Error('Mobile horizontal overflow: '+width);
 await page.screenshot({path:'runtime/demo-capture/mobile-'+phase+'.png',fullPage:true});
 }
 if(errors.length)throw new Error(JSON.stringify(errors));
 if(mobileChecks){await browser.close();console.log(JSON.stringify({phase,mobileChecks:true,pageErrors:errors}));return;}
 const recording=await page.video().path();await page.context().close();await browser.close();
 for(const clip of clips){require('node:child_process').execFileSync('ffmpeg',['-y','-v','error','-ss',String(clip.start),'-i',recording,'-t','6','-an','-vf','fps=24','-c:v','libx264','-preset','fast','-threads','2','-crf','23','runtime/demo-capture/'+clip.name+'-screen.mp4']);}
 console.log(JSON.stringify({phase,actualHostedUI:true,pageErrors:errors}));
})().catch(async e=>{if(page)await page.screenshot({path:'runtime/demo-capture/capture-failure.png',fullPage:true}).catch(()=>{});if(browser)await browser.close().catch(()=>{});console.error(e);process.exit(1)});
