// Capture actual hosted UI states. No response interception or simulated service data.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs');
(async()=>{
 const url=process.env.STORYPARITY_URL, phase=process.argv[2];
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route(url+'/**',route=>route.continue({headers:{...route.request().headers(),'X-Serverless-Authorization':'Bearer '+process.env.STORYPARITY_IDENTITY}}));
 await page.goto(url);
 await page.getByLabel('Reviewer access key').fill(process.env.STORYPARITY_REVIEWER_TOKEN);
 await page.getByRole('button',{name:'Open workspace'}).click();
 const projectsResponse=await page.request.get(url+'/api/projects',{headers:{'X-Serverless-Authorization':'Bearer '+process.env.STORYPARITY_IDENTITY,'Authorization':'Bearer '+process.env.STORYPARITY_REVIEWER_TOKEN}});
 const projects=await projectsResponse.json();
 const index=projects.findIndex(p=>p.id===process.env.STORYPARITY_CAPTURE_PROJECT);
 if(index<0)throw new Error('Capture project not found');
 await page.locator('nav button').nth(index).click();
 await page.getByRole('heading',{name:'Version inventory'}).waitFor();
 fs.mkdirSync('runtime/demo-capture',{recursive:true});
 async function snap(name){await page.screenshot({path:'runtime/demo-capture/'+name+'.png',fullPage:false});}
 if(phase==='before'){
   await snap('01-sources');
   await page.getByRole('button',{name:'02 Story specification'}).click();await snap('02-spec');
   await page.getByRole('button',{name:'03 Findings'}).click();
   await page.locator('video').evaluate(v=>{v.currentTime=10;v.pause();});
   await page.locator('video').evaluate(v=>new Promise(resolve=>{if(v.readyState>=2)resolve();else v.onloadeddata=resolve;}));
   await snap('03-findings');
   await page.locator('.findings-grid').scrollIntoViewIfNeeded();await snap('04-defects');
 }else if(phase==='proposal'){
   await page.getByRole('button',{name:'04 Repairs'}).click();await snap('05-proposal');
 }else if(phase==='after'){
   await page.getByRole('button',{name:'03 Findings'}).click();await snap('06-verified');
   await page.getByRole('button',{name:'05 Activity'}).click();
   await page.locator('.timeline details').first().locator('summary').click();await snap('07-evidence');
 }else{
   await page.getByRole('button',{name:'03 Findings'}).click();await snap('08-rollback');
 }
 if(errors.length)throw new Error(JSON.stringify(errors));
 await browser.close();console.log(JSON.stringify({phase,actualHostedUI:true,pageErrors:errors}));
})().catch(e=>{console.error(e);process.exit(1)});
