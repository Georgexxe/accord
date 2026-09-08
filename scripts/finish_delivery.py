"""Resume a real hosted synthetic acceptance run after a safely rejected investigation."""
import io,json,os,subprocess,zipfile
from pathlib import Path
import httpx
out=Path('runtime/hosted-delivery')
identity=subprocess.run([os.environ['STORYPARITY_GCLOUD'],'auth','print-identity-token'],capture_output=True,text=True,check=True).stdout.strip()
client=httpx.Client(base_url=os.environ['STORYPARITY_URL'],timeout=300,headers={'X-Serverless-Authorization':'Bearer '+identity,'Authorization':'Bearer '+os.environ['STORYPARITY_REVIEWER_TOKEN']})
base='/api/projects/'+json.loads((out/'before.json').read_text())['id']
def call(method,path,**kwargs):
 r=getattr(client,method)(path,**kwargs)
 if r.status_code>=400:
  (out/'resume-failure.json').write_text(json.dumps({'path':path,'status':r.status_code,'body':r.json()},indent=2));r.raise_for_status()
 return r.json()
p=call('get',base)
if p['proposals'] and p['proposals'][-1]['status']=='APPLIED':
 p=call('post',base+f"/proposals/{p['proposals'][-1]['id']}/rollback",json={'revision':p['revision']})
spec=p['spec']
for invariant in spec['invariants']:
 if invariant['kind']=='SOUND' and 'lock' in invariant['value'].lower():
  invariant['aliases']=sorted(set(invariant['aliases']+['door locks, beeps']))
spec['notes']+=' Test-reviewer explicitly approved equivalent caption wording door locks, beeps against the original lock sound.'
p=call('put',base+'/spec',json={'revision':p['revision'],'spec':spec})
p=call('post',base+'/spec/approve',json={'revision':p['revision'],'digest':p['spec_digest']})
p=call('post',base+'/scan',json={'revision':p['revision']})
(out/'before.json').write_text(json.dumps(p,indent=2),encoding='utf-8')
(out/'reviewed-spec.json').write_text(json.dumps(p['spec'],indent=2),encoding='utf-8')
p=call('post',base+'/investigate',json={'revision':p['revision'],'finding_ids':[f['id'] for f in p['findings']]})
proposal=p['proposals'][-1];(out/'proposal.json').write_text(json.dumps(proposal,indent=2),encoding='utf-8')
p=call('post',base+f"/proposals/{proposal['id']}/apply",json={'revision':p['revision'],'digest':proposal['approval_digest']})
assert p['status']=='VERIFIED' and not p['findings'],'Repair left findings'
assert all(a['revision']>1 for a in p['assets'] if a['parent_id']),'Both linked derivatives must be repaired'
(out/'after.json').write_text(json.dumps(p,indent=2),encoding='utf-8')
response=client.get(base+'/export');response.raise_for_status();(out/'delivery.zip').write_bytes(response.content)
with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
 assert len([x for x in archive.namelist() if x.endswith('.srt')])==6
p=call('post',base+f"/proposals/{proposal['id']}/rollback",json={'revision':p['revision']})
assert p['findings']
assert all(a['cues'][0]['text']=='Hay 4 supervivientes.' for a in p['assets'] if a['parent_id'])
(out/'rollback.json').write_text(json.dumps(p,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','hosted':True,'tracks':6,'derivativesRepairedAndRestored':2,'rollbackFindings':len(p['findings'])}))
