"""Build and release a tested image. All credentials are Secret Manager references."""
import argparse
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--gcloud', required=True)
p.add_argument('--project', default='project-ca8af2fe-5aff-496a-bd8')
p.add_argument('--tag', required=True, help='Unique immutable release identifier')
p.add_argument('--service', choices=['storyparity-staging', 'storyparity'], default='storyparity-staging')
p.add_argument('--clickhouse-host', default='10.88.0.2')
p.add_argument('--skip-build', action='store_true', help='Reuse previously tested immutable image')
p.add_argument('--public', action='store_true', help='Enable public Cloud Run invocation only when explicitly approved; app bearer auth remains required')
a = p.parse_args()
if not a.tag.replace('-', '').replace('.', '').isalnum() or a.tag == 'latest':
    p.error('Tag must be an immutable alphanumeric release identifier')
root = Path(__file__).resolve().parent.parent
image = f'us-central1-docker.pkg.dev/{a.project}/hackathon-apps/storyparity:{a.tag}'
def gc(*args, optional=False):
    r = subprocess.run([a.gcloud,*args,'--project='+a.project,'--quiet'],cwd=root,text=True,capture_output=True)
    if r.returncode and not optional:
        raise RuntimeError(r.stderr)
    if r.stdout:
        print(r.stdout,flush=True)
    return r

if not a.skip_build:
    gc('builds','submit','.','--config=deploy/cloudbuild.yaml','--substitutions=_IMAGE='+image)
digest=gc('artifacts','docker','images','describe',image,'--format=value(image_summary.digest)').stdout.strip()
if not digest.startswith('sha256:'):
    raise RuntimeError('Could not resolve immutable image digest')
image=image.rsplit(':',1)[0]+'@'+digest
gc('run','services','describe',a.service,'--region=us-central1','--format=value(status.latestReadyRevisionName)',optional=True)
env = {
    'STORYPARITY_STORE':'firestore',
    'STORYPARITY_MEDIA_BUCKET':a.project+'-storyparity-media',
    'STORYPARITY_FIRESTORE_COLLECTION':'storyparity_staging_projects' if a.service.endswith('-staging') else 'storyparity_projects',
    'GOOGLE_GENAI_USE_VERTEXAI':'true',
    'GOOGLE_CLOUD_PROJECT':a.project,
    'GOOGLE_CLOUD_LOCATION':'us-central1',
    'STATIC_DIR':'/app/frontend/dist',
    'CLICKHOUSE_HOST':a.clickhouse_host,
    'CLICKHOUSE_PORT':'8123',
    'CLICKHOUSE_SECURE':'false',
    'CLICKHOUSE_DATABASE':'storyparity_staging' if a.service.endswith('-staging') else 'storyparity',
    'CLICKHOUSE_USER':'storyparity_writer',
    'CLICKHOUSE_READ_USER':'storyparity_reader',
}
gc('run','deploy',a.service,'--image='+image,'--region=us-central1','--service-account=storyparity-runtime@'+a.project+'.iam.gserviceaccount.com','--cpu=1','--memory=1Gi','--min=0','--max=2','--concurrency=8','--timeout=300','--port=8080','--network=storyparity','--subnet=storyparity','--vpc-egress=private-ranges-only','--set-env-vars='+','.join(k+'='+v for k,v in env.items()),'--set-secrets=STORYPARITY_REVIEWER_TOKEN=storyparity-reviewer-token:latest,CLICKHOUSE_PASSWORD=storyparity-clickhouse-writer:latest,CLICKHOUSE_READ_PASSWORD=storyparity-clickhouse-reader:latest','--allow-unauthenticated' if a.public else '--no-allow-unauthenticated','--format=json')


