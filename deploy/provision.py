"""Provision the approved small StoryParity infrastructure. Never prints secret values."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--gcloud', required=True)
parser.add_argument('--project', default='project-ca8af2fe-5aff-496a-bd8')
parser.add_argument('--clickhouse-image', required=True, help='Pinned official image tag or digest')
args = parser.parse_args()
project = args.project
region, zone = 'us-central1', 'us-central1-a'
runtime = f'storyparity-runtime@{project}.iam.gserviceaccount.com'
database = f'storyparity-clickhouse@{project}.iam.gserviceaccount.com'
bucket = f'{project}-storyparity-media'

def gc(*command, data=None, optional=False):
    result = subprocess.run([args.gcloud, *command, '--project='+project, '--quiet', '--format=json'], input=data, capture_output=True, text=True)
    if result.returncode:
        if optional:
            return None
        raise RuntimeError(f'gcloud {command[:3]} failed: {result.stderr}')
    return json.loads(result.stdout) if result.stdout.strip() else {}

for account in ('storyparity-runtime', 'storyparity-clickhouse'):
    email = f'{account}@{project}.iam.gserviceaccount.com'
    if gc('iam','service-accounts','describe',email,optional=True) is None:
        gc('iam','service-accounts','create',account,'--display-name='+account)
    print('Service account ready:',account,flush=True)

for name in ('storyparity-clickhouse-writer','storyparity-clickhouse-reader','storyparity-reviewer-token'):
    if gc('secrets','describe',name,optional=True) is None:
        gc('secrets','create',name,'--replication-policy=automatic')
        gc('secrets','versions','add',name,'--data-file=-',data=secrets.token_urlsafe(48))
    gc('secrets','add-iam-policy-binding',name,'--member=serviceAccount:'+runtime,'--role=roles/secretmanager.secretAccessor')
    if 'clickhouse' in name:
        gc('secrets','add-iam-policy-binding',name,'--member=serviceAccount:'+database,'--role=roles/secretmanager.secretAccessor')
    print('Secret ready:',name,flush=True)

for role in ('roles/aiplatform.user','roles/datastore.user'):
    gc('projects','add-iam-policy-binding',project,'--member=serviceAccount:'+runtime,'--role='+role)
if gc('storage','buckets','describe','gs://'+bucket,optional=True) is None:
    gc('storage','buckets','create','gs://'+bucket,'--location='+region,'--uniform-bucket-level-access','--public-access-prevention')
gc('storage','buckets','add-iam-policy-binding','gs://'+bucket,'--member=serviceAccount:'+runtime,'--role=roles/storage.objectUser')
if gc('compute','networks','describe','storyparity',optional=True) is None:
    gc('compute','networks','create','storyparity','--subnet-mode=custom')
if gc('compute','networks','subnets','describe','storyparity','--region='+region,optional=True) is None:
    gc('compute','networks','subnets','create','storyparity','--network=storyparity','--region='+region,'--range=10.88.0.0/26','--enable-private-ip-google-access')
for name, source, ports in [('storyparity-clickhouse-private','10.88.0.0/26','tcp:8123'),('storyparity-iap-ssh','35.235.240.0/20','tcp:22'),('storyparity-iap-database','35.235.240.0/20','tcp:8123')]:
    if gc('compute','firewall-rules','describe',name,optional=True) is None:
        gc('compute','firewall-rules','create',name,'--network=storyparity','--direction=INGRESS','--action=ALLOW','--source-ranges='+source,'--rules='+ports,'--target-tags=storyparity-clickhouse')
if gc('compute','instances','describe','storyparity-clickhouse','--zone='+zone,optional=True) is None:
    gc('compute','instances','create','storyparity-clickhouse','--zone='+zone,'--machine-type=e2-medium','--subnet=storyparity','--private-network-ip=10.88.0.2','--tags=storyparity-clickhouse','--service-account='+database,'--scopes=cloud-platform','--image-family=debian-12','--image-project=debian-cloud','--boot-disk-size=20GB','--boot-disk-type=pd-standard','--no-boot-disk-auto-delete','--metadata=clickhouse-image='+args.clickhouse_image,'--metadata-from-file=startup-script='+str(Path(__file__).with_name('clickhouse-startup.sh')),'--shielded-secure-boot')
print(json.dumps({'host':'10.88.0.2','port':8123,'secure':False,'writer_user':'storyparity_writer','reader_user':'storyparity_reader','writer_secret':'storyparity-clickhouse-writer','reader_secret':'storyparity-clickhouse-reader','reviewer_secret':'storyparity-reviewer-token','media_bucket':bucket,'runtime_service_account':runtime,'network':'storyparity','subnet':'storyparity','zone':zone},indent=2))
