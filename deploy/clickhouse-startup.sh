#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq docker.io python3
systemctl enable --now docker
install -d -m 700 /etc/storyparity
install -d /var/lib/storyparity-clickhouse
python3 - <<'PY'
import base64, json, urllib.request, pathlib, hashlib
def metadata(path):
    req = urllib.request.Request('http://metadata.google.internal/computeMetadata/v1/'+path, headers={'Metadata-Flavor':'Google'})
    return urllib.request.urlopen(req).read().decode()
project = metadata('project/project-id')
token = json.loads(metadata('instance/service-accounts/default/token'))['access_token']
def secret(name):
    req = urllib.request.Request(f'https://secretmanager.googleapis.com/v1/projects/{project}/secrets/{name}/versions/latest:access',headers={'Authorization':'Bearer '+token})
    return base64.b64decode(json.load(urllib.request.urlopen(req))['payload']['data']).decode()
writer = hashlib.sha256(secret('storyparity-clickhouse-writer').encode()).hexdigest()
reader = hashlib.sha256(secret('storyparity-clickhouse-reader').encode()).hexdigest()
xml = f'''<clickhouse>
<profiles><storyparity_readonly><readonly>1</readonly><max_execution_time>30</max_execution_time><max_memory_usage>536870912</max_memory_usage></storyparity_readonly></profiles>
<users>
<default remove="remove"/>
<storyparity_writer><password_sha256_hex>{writer}</password_sha256_hex><networks><ip>::/0</ip></networks><profile>default</profile><quota>default</quota></storyparity_writer>
<storyparity_reader><password_sha256_hex>{reader}</password_sha256_hex><networks><ip>::/0</ip></networks><profile>storyparity_readonly</profile><quota>default</quota></storyparity_reader>
</users></clickhouse>'''
pathlib.Path('/etc/storyparity/users.xml').write_text(xml)
pathlib.Path('/etc/storyparity/server.xml').write_text('<clickhouse><listen_host>0.0.0.0</listen_host><max_server_memory_usage>2684354560</max_server_memory_usage><mark_cache_size>134217728</mark_cache_size><uncompressed_cache_size>67108864</uncompressed_cache_size></clickhouse>')
PY
chmod 644 /etc/storyparity/users.xml /etc/storyparity/server.xml
# Version is fixed by the provisioning metadata, never the mutable latest tag.
IMAGE=$(curl -fsS -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/clickhouse-image)
docker pull "$IMAGE"
docker rm -f storyparity-clickhouse 2>/dev/null || true
docker run -d --name storyparity-clickhouse --restart unless-stopped --memory 3g --cpus 2 --ulimit nofile=262144:262144 -p 8123:8123 -v /var/lib/storyparity-clickhouse:/var/lib/clickhouse -v /etc/storyparity/users.xml:/etc/clickhouse-server/users.d/storyparity.xml:ro -v /etc/storyparity/server.xml:/etc/clickhouse-server/config.d/storyparity.xml:ro "$IMAGE"
for attempt in $(seq 1 60); do
  if curl --fail --silent http://127.0.0.1:8123/ping >/dev/null; then
    python3 - <<'PY'
import base64, json, urllib.request
def get(url,headers):
    return urllib.request.urlopen(urllib.request.Request(url,headers=headers)).read()
base='http://metadata.google.internal/computeMetadata/v1/'
project=get(base+'project/project-id',{'Metadata-Flavor':'Google'}).decode()
token=json.loads(get(base+'instance/service-accounts/default/token',{'Metadata-Flavor':'Google'}))['access_token']
def password(name):
    data=json.loads(get(f'https://secretmanager.googleapis.com/v1/projects/{project}/secrets/{name}/versions/latest:access',{'Authorization':'Bearer '+token}))
    return base64.b64decode(data['payload']['data']).decode()
def query(user, secret, sql):
    auth=base64.b64encode((user+':'+password(secret)).encode()).decode()
    req=urllib.request.Request('http://127.0.0.1:8123/',data=sql.encode(),headers={'Authorization':'Basic '+auth})
    return urllib.request.urlopen(req).read().decode().strip()
for database in ('storyparity','storyparity_staging'):
    query('storyparity_writer','storyparity-clickhouse-writer','CREATE DATABASE IF NOT EXISTS '+database)
assert query('storyparity_reader','storyparity-clickhouse-reader','SELECT 1') == '1'
print('STORYPARITY_CLICKHOUSE_READY_DATABASES_AND_READER_VERIFIED')
PY
    exit 0
  fi
  sleep 3
done
echo STORYPARITY_CLICKHOUSE_STARTUP_FAILED
exit 1
