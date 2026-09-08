"""Record actual hosted states around a fresh synthetic acceptance repair."""
import json,os,subprocess
from pathlib import Path
import httpx
gc=os.environ['STORYPARITY_GCLOUD']
identity=subprocess.run([gc,'auth','print-identity-token'],capture_output=True,text=True,check=True).stdout.strip()
os.environ['STORYPARITY_IDENTITY']=identity
url=os.environ['STORYPARITY_URL']
client=httpx.Client(base_url=url,timeout=300,headers={'X-Serverless-Authorization':'Bearer '+identity,'Authorization':'Bearer '+os.environ['STORYPARITY_REVIEWER_TOKEN']})
project_id=json.loads(Path('runtime/hosted-delivery/rollback.json').read_text())['id']
if os.getenv('STORYPARITY_SEED_PRODUCTION')=='1':
    from app.store import Store
    from app.domain import uid
    source=Store().get(project_id)
    source.title='Protocol Kepler-9 — original demo'
    source.snapshot_id=None;source.findings=[];source.status='READY_FOR_SCAN'
    source.record('demo_imported',source='Actual staging acceptance; original synthetic inputs. Reindex required in production.')
    os.environ['STORYPARITY_FIRESTORE_COLLECTION']='storyparity_projects'
    production=Store()
    existing=[p for p in production.list() if p['title']==source.title]
    if existing:
        project_id=existing[0]['id']
    else:
        source.id=uid();production.save(source,None);project_id=source.id
os.environ['STORYPARITY_CAPTURE_PROJECT']=project_id
base='/api/projects/'+project_id
def call(method,path,**kwargs):
    r=getattr(client,method)(path,**kwargs);r.raise_for_status();return r.json()
def capture(phase):subprocess.run(['node','scripts/capture_cloud.cjs',phase],check=True)
p=call('get',base)
if p['proposals'] and p['proposals'][-1]['status']=='APPLIED':
    p=call('post',base+f"/proposals/{p['proposals'][-1]['id']}/rollback",json={'revision':p['revision']})
if not p['snapshot_id']:
    p=call('post',base+'/scan',json={'revision':p['revision']})
capture('before')
p=call('post',base+'/investigate',json={'revision':p['revision'],'finding_ids':[f['id'] for f in p['findings']]})
proposal=p['proposals'][-1]
# Explicit synthetic test-reviewer edits, not attributed to the model.
sound_assets={f['asset_id'] for f in p['findings'] if f['kind']=='SOUND'}
clues={(f['asset_id'],f['cue_id']) for f in p['findings'] if f['kind']=='CLUE'}
for change in proposal['changes']:
    if change['asset_id'] in sound_assets and change['operation']=='INSERT':
        change['replacement']['text']='[Door locks, beeps]'
        change['replacement']['start']=20.0;change['replacement']['end']=21.0
    if (change['asset_id'],change['cue_id']) in clues and change['replacement']:
        change['replacement']['box']={'x':.3,'y':.1,'width':.4,'height':.15}
proposal['rationale']+=' Test reviewer aligned the sound caption with the approved alias and placed the subtitle above the source clue.'
proposal.pop('approval_digest',None)
p=call('put',base+f"/proposals/{proposal['id']}",json={'revision':p['revision'],'proposal':proposal})
proposal=p['proposals'][-1];capture('proposal')
p=call('post',base+f"/proposals/{proposal['id']}/apply",json={'revision':p['revision'],'digest':proposal['approval_digest']})
assert p['status']=='VERIFIED' and not p['findings']
capture('after')
Path('runtime/demo-capture/verified.json').write_text(json.dumps(p,indent=2),encoding='utf-8')
p=call('post',base+f"/proposals/{proposal['id']}/rollback",json={'revision':p['revision']})
assert p['findings'];capture('rollback')
print(json.dumps({'status':'PASS','actualHostedScreens':8,'rollbackFindings':len(p['findings'])}))
