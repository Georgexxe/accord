"""Exercise complete API workflow with actual Vertex, ClickHouse MCP and durable storage.
Uses only the explicitly synthetic demo and a test reviewer credential. No simulated service results.
"""
import io
import json
import os
import zipfile
from pathlib import Path
from fastapi.testclient import TestClient
from app.api import app
import httpx
import subprocess

remote=os.getenv('STORYPARITY_URL')
client=httpx.Client(base_url=remote,timeout=300) if remote else TestClient(app)
if remote:
    token=subprocess.run([os.environ['STORYPARITY_GCLOUD'],'auth','print-identity-token'],capture_output=True,text=True,check=True).stdout.strip()
    client.headers['X-Serverless-Authorization']='Bearer '+token
client.headers['Authorization']='Bearer '+os.environ['STORYPARITY_REVIEWER_TOKEN']
evidence=Path('runtime/hosted-delivery' if remote else 'runtime/live-delivery');evidence.mkdir(parents=True,exist_ok=True)
def call(method,path,**kwargs):
    response=getattr(client,method)(path,**kwargs)
    if response.status_code>=400:
        (evidence/'failure.json').write_text(json.dumps({'path':path,'status':response.status_code,'body':response.json()},indent=2),encoding='utf-8')
        raise RuntimeError(f'Live API step failed: {path}: {response.status_code}')
    return response.json()
p=call('post','/api/projects',json={'title':'Protocol Kepler-9 — live acceptance test','script':Path('demo/master-script.txt').read_text(encoding='utf-8')})
base='/api/projects/'+p['id']
p=call('post',base+'/media',data={'revision':p['revision']},files={'file':('master.mp4',Path('demo/master.mp4').read_bytes(),'video/mp4')})
for filename,locale,kind in [('spanish-errors.json','es','SUBTITLE'),('english-sdh-missing-lock.json','en','SDH'),('english-ad-overlap.json','en','AD'),('english-dub-control.json','en','DUB')]:
    p=call('post',base+'/assets',data={'revision':p['revision'],'locale':locale,'kind':kind},files={'file':(filename,Path('demo/'+filename).read_bytes(),'application/json')})
parent=p['assets'][0]['id']
for name,offset,start in [('spanish-recap',9,1),('spanish-trailer',8,2)]:
    cues=[{'id':'1','start':start,'end':start+4,'text':'Hay 4 supervivientes.'}]
    p=call('post',base+'/assets',data={'revision':p['revision'],'locale':'es','kind':'SUBTITLE','parent_id':parent,'master_offset':offset},files={'file':(name+'.json',json.dumps(cues).encode(),'application/json')})
p=call('post',base+'/extract',json={'revision':p['revision']})
(evidence/'extracted-spec.json').write_text(json.dumps(p['spec'],indent=2),encoding='utf-8')
# Explicit test-reviewer correction from the original fixture's measured speech annotations.
# Preserve raw model output above; these edits are never attributed to Gemini.
spec=p['spec']
spec['invariants']=[i for i in spec['invariants'] if i['kind']!='DIALOGUE']
for speech in json.loads(Path('demo/speech-intervals.json').read_text()):
    spec['invariants'].append({'kind':'DIALOGUE','description':speech['text'],'value':speech['text'],'start':speech['start'],'end':speech['end'],'evidence':'Test-reviewer annotation from original generated speech waveform: '+speech['text'],'aliases':[]})
for invariant in spec['invariants']:
    if invariant['kind']=='REVEAL' and 'Mara' in invariant['value']:
        invariant['aliases']=sorted(set(invariant['aliases']+['Mara']))
    if invariant['kind']=='SOUND' and 'lock' in invariant['value'].lower():
        invariant['aliases']=sorted(set(invariant['aliases']+['door locks, beeps']))
spec['notes']+=' Test reviewer replaced dialogue intervals with measured synthetic-source annotations and approved the proper-name alias Mara and sound-caption wording door locks, beeps. Raw Gemini extraction is retained separately.'
p=call('put',base+'/spec',json={'revision':p['revision'],'spec':spec})
(evidence/'reviewed-spec.json').write_text(json.dumps(p['spec'],indent=2),encoding='utf-8')
# Test-reviewer approves the reviewed specification only for this synthetic acceptance run.
p=call('post',base+'/spec/approve',json={'revision':p['revision'],'digest':p['spec_digest']})
p=call('post',base+'/scan',json={'revision':p['revision']})
(evidence/'before.json').write_text(json.dumps(p,indent=2),encoding='utf-8')
print(json.dumps({'stage':'scanned','project_id':p['id'],'kinds':sorted({f['kind'] for f in p['findings']}),'findings':len(p['findings'])}),flush=True)
assert {'NUMBER','REVEAL','SOUND','DIALOGUE','CLUE'} <= {f['kind'] for f in p['findings']},'Expected all five defect classes from original scene'
p=call('post',base+'/investigate',json={'revision':p['revision'],'finding_ids':[f['id'] for f in p['findings']]})
proposal=p['proposals'][-1]
(evidence/'proposal.json').write_text(json.dumps(proposal,indent=2),encoding='utf-8')
p=call('post',base+f"/proposals/{proposal['id']}/apply",json={'revision':p['revision'],'digest':proposal['approval_digest']})
(evidence/'after.json').write_text(json.dumps(p,indent=2),encoding='utf-8')
assert p['status']=='VERIFIED' and not p['findings'],'Repair left findings requiring review'
response=client.get(base+'/export');assert response.status_code==200
(evidence/'delivery.zip').write_bytes(response.content)
with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
    assert len([n for n in archive.namelist() if n.endswith('.srt')])==6
p=call('post',base+f"/proposals/{proposal['id']}/rollback",json={'revision':p['revision']})
assert p['findings'],'Rollback must restore original findings'
(evidence/'rollback.json').write_text(json.dumps(p,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','project_id':p['id'],'real_multimodal':True,'repair_verified':True,'rollback_findings':len(p['findings']),'evidence':str(evidence)}))
