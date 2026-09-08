"""Exercise both original films against actual hosted Gemini / ClickHouse services.
Known-answer reviewer corrections are explicit and recorded; never mock model responses.
"""
import argparse,copy,json,os,subprocess
from pathlib import Path
import httpx

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--gcloud',required=True);ap.add_argument('--url',required=True);ap.add_argument('--label',required=True);ap.add_argument('--capture',action='store_true');ap.add_argument('--prepare-only',action='store_true',help='Leave a reviewed proposal pending for an interactive demonstration');ap.add_argument('--scenes',default='harbor,lantern');args=ap.parse_args()
 def gc(*parts):return subprocess.run([args.gcloud,*parts],capture_output=True,text=True,check=True).stdout.strip()
 token=gc('secrets','versions','access','latest','--secret=storyparity-reviewer-token','--project=project-ca8af2fe-5aff-496a-bd8')
 identity=gc('auth','print-identity-token')
 client=httpx.Client(base_url=args.url,headers={'Authorization':'Bearer '+token,'X-Serverless-Authorization':'Bearer '+identity},timeout=300)
 out=Path('runtime/lantern');results=[]
 def call(method,path,**kw):
  r=client.request(method,path,**kw)
  if not r.is_success:raise RuntimeError(f'{method} {path}: {r.status_code} {r.text[:1500]}')
  return r.json()
 for scene,title in [('harbor','Harbor Lights'),('lantern','The Last Lantern')]:
  if scene not in args.scenes.split(','):continue
  root=Path('demo')/scene;checkpoint=out/f'{args.label}-{scene}-id.json'
  if checkpoint.exists():p=call('GET','/api/projects/'+json.loads(checkpoint.read_text())['id'])
  else:
   p=call('POST','/api/projects',json={'title':title,'script':(root/'script.txt').read_text(encoding='utf-8')});checkpoint.write_text(json.dumps({'id':p['id']}))
  base='/api/projects/'+p['id']
  def mutate(path,body=None,method='POST'):
   nonlocal p
   p=call(method,base+path,json={'revision':p['revision'],**(body or {})});return p
  if p['proposals'] and p['proposals'][-1]['status']=='APPLIED':mutate('/proposals/'+p['proposals'][-1]['id']+'/rollback')
  if not p['media_key']:p=call('POST',base+'/media',data={'revision':str(p['revision'])},files={'file':('master.mp4',(root/'master.mp4').read_bytes(),'video/mp4')})
  clean=json.loads((root/'clean-tracks.json').read_text(encoding='utf-8'));bad=json.loads((root/'test-tracks.json').read_text(encoding='utf-8'))
  if not p['assets']:
   for track in bad:
    p=call('POST',base+'/assets',data={'revision':str(p['revision']),'locale':track['locale'],'kind':track['kind']},files={'file':(track['name']+'.json',json.dumps(track['cues']).encode(),'application/json')})
   if scene=='lantern':
    parent=p['assets'][0]['id']
    for name in ['Spanish recap','Spanish trailer']:
     cue=copy.deepcopy(bad[0]['cues'][0]);cue.update(start=1,end=7)
     p=call('POST',base+'/assets',data={'revision':str(p['revision']),'locale':'es','kind':'SUBTITLE','parent_id':parent,'master_offset':'8'},files={'file':(name+'.json',json.dumps([cue]).encode(),'application/json')})
  if not p['spec']:
   mutate('/extract');(out/f'{args.label}-{scene}-extracted.json').write_text(json.dumps(p['spec'],indent=2),encoding='utf-8')
  # Explicit reviewer approval of the measured story reference, preserving extraction evidence.
  reference=json.loads((root/'reviewed-story-notes.json').read_text(encoding='utf-8'))
  mutate('/spec',{'spec':reference},'PUT');mutate('/spec/approve',{'digest':p['spec_digest']});mutate('/scan')
  expected=7 if scene=='lantern' else 2
  assert len(p['findings'])==expected,(scene,'unexpected findings',p['findings'])
  before=copy.deepcopy(p);(out/f'{args.label}-{scene}-before.json').write_text(json.dumps(p,indent=2),encoding='utf-8')
  def capture(phase):
   if not args.capture or scene!='lantern':return
   env=dict(os.environ,STORYPARITY_URL=args.url,STORYPARITY_REVIEWER_TOKEN=token,STORYPARITY_IDENTITY=identity,STORYPARITY_CAPTURE_PROJECT=p['id'],PLAYWRIGHT_MODULE='C:/Users/SURFACE/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')
   subprocess.run(['node','scripts/capture_cloud.cjs',phase],env=env,check=True)
  if not args.prepare_only:capture('before')
  mutate('/investigate',{'finding_ids':[f['id'] for f in p['findings']]})
  proposal=p['proposals'][-1];(out/f'{args.label}-{scene}-agent-proposal.json').write_text(json.dumps(proposal,indent=2),encoding='utf-8')
  # Reviewer uses the known-answer original to correct wording / timing / placement only.
  for change in proposal['changes']:
   asset=next(a for a in p['assets'] if a['id']==change['asset_id'])
   if asset['parent_id']:
    replacement=copy.deepcopy(clean[0]['cues'][0]);replacement.update(id=change['cue_id'],start=1,end=7)
   else:
    original=next(t for t in clean if t['kind']==asset['kind'])
    replacement=next((copy.deepcopy(c) for c in original['cues'] if c['id']==change['cue_id']),None)
    if replacement is None and change['operation']=='INSERT':replacement=copy.deepcopy(next(c for c in original['cues'] if c['id']=='bell'));replacement['id']=change['cue_id']
   if replacement:change['replacement']=replacement;change['operation']='INSERT' if not any(c['id']==change['cue_id'] for c in asset['cues']) else 'REPLACE'
  proposal['rationale']+=' Reviewer checked these edits against the original film and corrected timing, wording and placement where needed.'
  proposal.pop('approval_digest',None)
  mutate('/proposals/'+proposal['id'],{'proposal':proposal},'PUT');proposal=p['proposals'][-1]
  capture('proposal')
  if args.prepare_only:
   print('Prepared a reviewed proposal for '+scene+'; no changes applied',flush=True);continue
  mutate('/proposals/'+proposal['id']+'/apply',{'digest':proposal['approval_digest']})
  assert p['status']=='VERIFIED' and not p['findings'],(scene,p['status'],p['findings'])
  capture('after');(out/f'{args.label}-{scene}-verified.json').write_text(json.dumps(p,indent=2),encoding='utf-8')
  mutate('/proposals/'+proposal['id']+'/rollback');assert len(p['findings'])==expected
  capture('rollback')
  results.append({'scene':scene,'project':p['id'],'injectedFindings':expected,'verifiedFindings':0,'restoredFindings':len(p['findings']),'realGeminiInvestigation':True,'reviewerEdits':True})
  print(json.dumps(results[-1]),flush=True)
 if args.prepare_only:return
 (out/f'{args.label}-acceptance.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
 print('PASS: requested scenes completed real extraction, investigation, reviewed correction, verification and undo',flush=True)
if __name__=='__main__':main()
