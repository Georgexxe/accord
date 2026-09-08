# Verified live infrastructure — 8 September 2026

Provisioned with explicit user approval of the resource stack and ongoing charges:

| Resource | Identifier |
| --- | --- |
| Project | `project-ca8af2fe-5aff-496a-bd8` |
| VM | `storyparity-clickhouse`, `us-central1-a`, e2-medium, 20 GiB persistent disk |
| VPC / subnet | `storyparity` / `storyparity`, `10.88.0.0/26` |
| Private ClickHouse | `10.88.0.2:8123`, HTTP on restricted network |
| Database version | `26.3.12.3` |
| Databases | `storyparity`, `storyparity_staging` |
| Runtime service account | `storyparity-runtime@project-ca8af2fe-5aff-496a-bd8.iam.gserviceaccount.com` |
| VM service account | `storyparity-clickhouse@project-ca8af2fe-5aff-496a-bd8.iam.gserviceaccount.com` |
| Private bucket | `project-ca8af2fe-5aff-496a-bd8-storyparity-media` |
| Writer secret | `storyparity-clickhouse-writer` |
| Reader secret | `storyparity-clickhouse-reader` |
| Reviewer secret | `storyparity-reviewer-token` |

Passwords are random, generated in process memory, stored in Secret Manager, and never included in this repository. Reader username is `storyparity_reader`; writer is `storyparity_writer`.

VM bootstrap emitted `STORYPARITY_CLICKHOUSE_READY_DATABASES_AND_READER_VERIFIED` at 14:26:49 UTC. The local IAP tunnel was verified on loopback port 18123 with `/ping` returning `Ok.`.

`check_connections.py`, executed through `local_cloud.py`, exited 0 and verified:

- Server version `26.3.12.3` and selected database `storyparity_staging`.
- Server-side readonly setting equals `1` for the reader.
- Official `mcp-clickhouse` package `0.6.0`, `run_query`, executed `SELECT 1 AS value WHERE 1 = 0` against the real server and returned zero rows.
- Measured initial subprocess/query duration: 18,526 ms over IAP, including MCP startup. This is a connectivity observation, not a latency benchmark.

## IAM-private staging release

Staging application deployed after the main agent's real Vertex/MCP investigation and regression checks:

- URL: `https://storyparity-staging-cus2bs7tpq-uc.a.run.app` (Google IAM authentication required).
- Current revision: `storyparity-staging-00004-rdq`, ready at 15:16:36 UTC.
- Current Cloud Build: `29993769-2a09-4345-9070-da38873722ab`, SUCCESS, including Trivy's fixable-critical vulnerability gate.
- Current image digest: `sha256:f9eb58ec17e6a38dd5c320ae4ae666ef00dd425aeaca82774dc7faf27d3b0a3e`; revision deploys the digest directly.
- This staging update adds read-only complete-repair preview validation for the investigator; the same image has passed hosted acceptance and is promoted to production.
- Previous rollback revision: `storyparity-staging-00003-v2k` (build `5a658ca3-e8e9-4d00-8a96-b05f40452b8d`).
- Health ready, version 2.0.0; absent reviewer credential rejected with 401; authenticated project read and frontend entry both return 200.
- Service IAM policy has no public invoker grant.

The main agent confirmed hosted final03 acceptance: six tracks across all five detector classes, seven findings, real ADK proposal, exact approval, live MCP verification with zero remaining findings, six-SRT export, and rollback restoring seven findings and both linked derivatives. See `READINESS.md` for stop/restart, release and rollback procedures.

## Public production release

After explicit user approval of public app access, accepted final03 was deployed to production:

- Public URL: `https://storyparity-cus2bs7tpq-uc.a.run.app`.
- Revision: `storyparity-00002-r2p`, ready at 15:21:15 UTC.
- Image digest: `sha256:f9eb58ec17e6a38dd5c320ae4ae666ef00dd425aeaca82774dc7faf27d3b0a3e`.
- Production Firestore collection: `storyparity_projects`; ClickHouse database: `storyparity`.
- Cloud Run invocation is public; application bearer authentication remains enforced.
- Without a Google identity token: page 200, health ready 200, private API without reviewer credential 401, private API with reviewer credential 200.
- No production data was seeded during deployment.

`release.py --public` supports explicitly approved public releases. Omit the flag for IAM-private staging. Releasing production without `--public` makes its invocation private again.



## Accord interface release — 8 September 2026

The customer-facing product is now Accord. Existing Cloud Run URLs, storage namespaces and access codes remain compatible.

- Production revision: `storyparity-00004-5dq`.
- Staging revision: `storyparity-staging-00006-26r`.
- Immutable image: `sha256:2b55c28a45f695a292be2c24f0efc0d2c635671c85589b0bd77d185751537d43`.
- Cloud build and scan passed. Staging health, frontend, authenticated reads and missing-token rejection passed.
- All 61 backend tests passed. Fresh production desktop/mobile capture completed with no JavaScript errors or horizontal page overflow, including the Sources table.
- The reviewed repair passed configured checks; undo restored seven original findings. The demo film title treatment was updated while preserving its audio and story timecodes.
- Public source: https://github.com/Georgexxe/accord.
