// Capture actual hosted UI states. No response interception or simulated service data.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs');
(async()=>{
 const url=process.env.STORYPARITY_URL, phase=process.argv[2];
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
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
 await page.waitForFunction(()=>{const v=document.querySelector('video');return v&&v.readyState>=2;},undefined,{timeout:30000});
 fs.mkdirSync('runtime/demo-capture',{recursive:true});
 async function snap(name){await page.screenshot({path:'runtime/demo-capture/'+name+'.png',fullPage:false});}
 if(phase==='before'){
   await snap('01-sources');
   await page.setViewportSize({width:390,height:844});
   if(await page.evaluate(()=>document.body.scrollWidth)>390)throw new Error('Sources mobile overflow');
   await page.screenshot({path:'runtime/demo-capture/mobile-sources.png',fullPage:true});
   await page.setViewportSize({width:1440,height:1000});
   await page.getByRole('button',{name:'Story notes',exact:true}).click();await snap('02-spec');
   await page.getByRole('button',{name:'Review',exact:true}).click();
   await page.locator('video').evaluate(v=>{v.currentTime=10;v.pause();});
   await page.waitForFunction(()=>document.querySelector('video')?.readyState>=2,undefined,{timeout:20000});
   await snap('03-findings');
   await page.locator('.findings-grid').scrollIntoViewIfNeeded();await snap('04-defects');
 }else if(phase==='proposal'){
   await page.getByRole('button',{name:'Changes',exact:true}).click();await snap('05-proposal');
 }else if(phase==='after'){
   await page.getByRole('button',{name:'Review',exact:true}).click();await snap('06-verified');
   await page.getByRole('button',{name:'History',exact:true}).click();
   await snap('07-evidence');
 }else{
   await page.getByRole('button',{name:'Review',exact:true}).click();await snap('08-rollback');
 }
 await page.setViewportSize({width:390,height:844});
 const width=await page.evaluate(()=>document.body.scrollWidth);
 if(width>390)throw new Error('Mobile horizontal overflow: '+width);
 await page.screenshot({path:'runtime/demo-capture/mobile-'+phase+'.png',fullPage:true});
 if(errors.length)throw new Error(JSON.stringify(errors));
 await browser.close();console.log(JSON.stringify({phase,actualHostedUI:true,pageErrors:errors}));
})().catch(e=>{console.error(e);process.exit(1)});
