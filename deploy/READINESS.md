# Deployment readiness — 8 September 2026

Verified by read-only gcloud checks against `project-ca8af2fe-5aff-496a-bd8`:

- Active user authentication works; project billing is enabled.
- Cloud Run, Vertex AI, Cloud Build, Artifact Registry, Firestore, IAM and Secret Manager APIs are enabled.
- Existing native Firestore `(default)` database is in `us-central1`.
- Docker repository `us-central1-docker.pkg.dev/project-ca8af2fe-5aff-496a-bd8/hackathon-apps` exists.
- Existing Cloud Run applications and storage buckets belong to other products; do not reuse their secrets or media locations.
- No ClickHouse-related secret was listed. No configured ClickHouse endpoint was provided to this task.
- Compute Engine API is disabled; no existing VM was verified.
- Local Application Default Credential token refresh failed. User CLI credentials are separate from ADC. Cloud Run should use its own service account through ADC; do not upload a user credential file.

## Concrete infrastructure scope

One same-origin Cloud Run service serves the React bundle and authenticated FastAPI endpoints. Attach a dedicated `storyparity-runtime` service account. Use the existing Firestore database with a dedicated application collection; implement revision checks through Firestore transactions. Keep media in a new private regional bucket and return media only through authenticated API reads. Keep reviewer and ClickHouse passwords in new Secret Manager secrets.

Grant the runtime account `roles/aiplatform.user` and `roles/datastore.user` at project scope, `roles/storage.objectUser` on the dedicated bucket, and `roles/secretmanager.secretAccessor` on only its secrets. Avoid project-wide secret access and service-account key files. Firestore roles apply across the database: document that isolation limitation for this initial single-product service account deployment.

Initial Cloud Run limits: region `us-central1`, 1 CPU, 1 GiB memory, concurrency 8, min instances 0, max instances 2, request timeout 300 seconds. `release.py` deploys IAM-private by default. App endpoints also require a reviewer bearer token. For private staging requests send the Google identity token through `X-Serverless-Authorization` and the app token through `Authorization`. Public access is a separate explicit release decision. Upload and per-project state limits must remain below the Firestore document size limit. Scale memory/concurrency only after a measured staging run.

ClickHouse must run against a real persistent database. The concrete deployment in `provision.py` uses e2-medium (4 GiB, 2 shared vCPUs), 20 GiB standard persistent disk, private HTTP ingress from a dedicated `/26` subnet plus IAM-authenticated IAP administration, and separate database reader and writer passwords in Secret Manager. The VM uses an external address for outbound package/image downloads; no public database ingress is allowed. This incurs ongoing VM, disk and external address charges, plus storage/AI/application usage. Initial automatic approval review blocked provisioning; the user subsequently explicitly approved the exact resource stack and ongoing charges. Provisioning is now authorized.

The proposed reader uses a server-enforced readonly profile; writer and reader passwords are SHA-256 hashes in the VM configuration, with original random secrets held in Secret Manager. The dedicated VM account can access only those two secrets. Runtime obtains credentials through the attached service account. The initial VM is a small demonstration deployment without replication or automated backup; it is not a high-availability database service.

Direct VPC uses the dedicated subnet and `private-ranges-only` egress, avoiding a billed VPC connector and Cloud NAT. Google requires `/26` or larger for this configuration: [official Direct VPC documentation](https://docs.cloud.google.com/run/docs/configuring/vpc-direct-vpc). The self-hosted Firecrawl capture failed because WSL exited -1; this failure is recorded in the workspace research archive.

For a local integration test, open an IAM-authenticated IAP tunnel bound to loopback:

```powershell
gcloud compute start-iap-tunnel storyparity-clickhouse 8123 --local-host-port=127.0.0.1:18123 --zone=us-central1-a --project=project-ca8af2fe-5aff-496a-bd8
```

The firewall permits port 8123 from only the private subnet and Google's IAP range `35.235.240.0/20`. The tunnel still requires the appropriate Google IAM permission and ClickHouse credentials. Use `CLICKHOUSE_HOST=127.0.0.1`, `CLICKHOUSE_PORT=18123`, `CLICKHOUSE_SECURE=false` locally. Retrieve secrets only into process memory, never terminal output or tracked files. Close the tunnel when testing ends.

## Release gates

1. Backend tests, frontend type check/build and dependency scan succeed.
2. Real Vertex invocation and official MCP read against ClickHouse succeed.
3. Integration test performs ingest, spec approval, detect, propose, exact approval, apply, re-query, verify, rollback and export.
4. Build immutable image with `deploy/cloudbuild.yaml`; never deploy `latest`.
5. Deploy a staging service with independent collection/media prefix and secrets; verify authenticated API, browser workflow, process restart persistence and failure behavior.
6. Deploy the verified image to the public application, then repeat health/authentication smoke checks. Record the service URL and revision.

## Rollback

Capture the serving revision before release:

```powershell
gcloud run services describe storyparity --region us-central1 --format='value(status.latestReadyRevisionName)'
```

Restore traffic to the recorded revision:

```powershell
gcloud run services update-traffic storyparity --region us-central1 --to-revisions=RECORDED_REVISION=100
```

Recheck `/api/health`, unauthenticated private endpoints (must reject), and an authenticated read. Traffic rollback does not revert persisted application data. Keep schema readers backward compatible; application patch rollback uses revision-bound snapshots, never overwrite the database wholesale.

## Packaging contract

Build from the repository root using `deploy/Dockerfile`. Frontend files are installed at `/app/frontend/dist`; backend must mount `STATIC_DIR` after API routes. Public liveness endpoint is `/api/health`. Container starts `app.main:app`, one worker, port 8080. Runtime dependencies must include official `mcp-clickhouse`, Google ADK/GenAI, Firestore and Cloud Storage libraries before image build.

## Cost control and shutdown

Stop the database while the demo is inactive:

```powershell
gcloud compute instances stop storyparity-clickhouse --zone us-central1-a --project project-ca8af2fe-5aff-496a-bd8
```

This stops VM compute billing; retained disks still incur charges. Restart with `instances start` using the same arguments. Stop disables all application functionality that requires ClickHouse. The boot disk is created with automatic deletion disabled to preserve database state if the VM is deleted. Full teardown requires a separate explicit decision to remove retained data; do not infer data deletion from a stop request. Cloud Run scales to zero with no requests and has max instances 2; Vertex calls, build/scanning, Firestore, storage and Secret Manager have independent usage charges.

