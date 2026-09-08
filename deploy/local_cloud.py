"""Run a Python test/server with cloud credentials held only in process memory.

Usage: python deploy/local_cloud.py --gcloud PATH -- script.py [arguments]
Requires the loopback IAP tunnel on port 18123. No credential file is written.
"""
import argparse
import datetime
import os
import runpy
import subprocess
import sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--gcloud', required=True)
p.add_argument('--project', default='project-ca8af2fe-5aff-496a-bd8')
p.add_argument('--cloud-store', action='store_true', help='Use isolated staging Firestore and private bucket')
p.add_argument('script', nargs=argparse.REMAINDER)
a = p.parse_args()
script = a.script[1:] if a.script and a.script[0] == '--' else a.script
if not script:
    p.error('Specify a Python script after --')

def captured(*args):
    result = subprocess.run([a.gcloud,*args,'--project='+a.project,'--quiet'],capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError('Cloud credential operation failed; check gcloud authentication and IAM permissions')
    return result.stdout.strip()

for env, secret in [('CLICKHOUSE_PASSWORD','storyparity-clickhouse-writer'),('CLICKHOUSE_READ_PASSWORD','storyparity-clickhouse-reader'),('STORYPARITY_REVIEWER_TOKEN','storyparity-reviewer-token')]:
    os.environ[env]=captured('secrets','versions','access','latest','--secret='+secret)
os.environ.update(CLICKHOUSE_HOST='127.0.0.1', CLICKHOUSE_PORT='18123', CLICKHOUSE_SECURE='false', CLICKHOUSE_USER='storyparity_writer', CLICKHOUSE_READ_USER='storyparity_reader', CLICKHOUSE_DATABASE='storyparity_staging', GOOGLE_CLOUD_PROJECT=a.project, GOOGLE_CLOUD_LOCATION='us-central1', GOOGLE_GENAI_USE_VERTEXAI='true')
if a.cloud_store:
    os.environ.update(STORYPARITY_STORE='firestore', STORYPARITY_FIRESTORE_COLLECTION='storyparity_staging_projects', STORYPARITY_MEDIA_BUCKET=a.project+'-storyparity-media')

# Resolve the authorized local CLI account through the normal Google credential
# interface; refreshes do not persist an ADC file or reveal the access token.
import google.auth
from google.auth.credentials import Credentials
class LocalCliCredentials(Credentials):
    def refresh(self, request):
        self.token = captured('auth','print-access-token')
        self.expiry = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(minutes=50)
credentials = LocalCliCredentials()
credentials.refresh(None)
google.auth.default = lambda *args, **kwargs: (credentials, a.project)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
sys.argv = script
runpy.run_path(script[0],run_name='__main__')
