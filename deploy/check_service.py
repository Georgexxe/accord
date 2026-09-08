"""Smoke-test a private Cloud Run revision without printing authentication tokens."""
import argparse
import json
import subprocess
import urllib.error
import urllib.request

p=argparse.ArgumentParser()
p.add_argument('--gcloud',required=True)
p.add_argument('--url',required=True)
p.add_argument('--project',default='project-ca8af2fe-5aff-496a-bd8')
p.add_argument('--public',action='store_true',help='Check approved public invocation without a Google identity token')
a=p.parse_args()
def credential(*args):
    r=subprocess.run([a.gcloud,*args,'--project='+a.project,'--quiet'],capture_output=True,text=True)
    if r.returncode: raise RuntimeError('Credential retrieval failed')
    return r.stdout.strip()
identity=None if a.public else credential('auth','print-identity-token')
reviewer=credential('secrets','versions','access','latest','--secret=storyparity-reviewer-token')
def get(path, authenticated=False):
    headers={'X-Serverless-Authorization':'Bearer '+identity} if identity else {}
    if authenticated: headers['Authorization']='Bearer '+reviewer
    try:
        r=urllib.request.urlopen(urllib.request.Request(a.url.rstrip('/')+path,headers=headers),timeout=60)
        return r.status,r.read()
    except urllib.error.HTTPError as e:
        return e.code,e.read()
status,body=get('/api/health')
assert status==200,(status,body)
print('Health:',json.loads(body))
status,_=get('/api/projects')
assert status in (401,403),status
print('Missing app credential rejected:',status)
status,body=get('/api/projects',True)
assert status==200,(status,body)
print('Authenticated project read:',status)
status,body=get('/')
assert status==200 and b'id="root"' in body,(status,'React entry point missing')
print('Frontend entry point:',status)
