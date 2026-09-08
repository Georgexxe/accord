# StoryParity implementation contract

Build every stage of the approved research workflow, prioritizing correctness over the hackathon deadline. Original source is preserved in Downloads; this workspace copy is the implementation repository.

## Acceptance criteria
- Authenticated reviewer uploads a master clip, script and SRT/VTT/JSON tracks. Inputs are bounded, parsed and versioned with immutable content hashes.
- Gemini on Google Cloud extracts structured, timecoded candidate story facts from master media/script. A reviewer approves the exact spec version before detection.
- Official mcp-clickhouse reads real indexed cues and lineage. Database failure never falls back to simulated success. Separate writer updates analytical versions.
- Detectors support numeric meaning, premature reveals, missing plot sound in SDH, AD/dialogue overlap, and subtitle/clue collision. Semantic judgments include evidence and may abstain; timing is deterministic. Controls are independently labelled.
- Real ADK investigation gathers evidence through tools and returns a structured proposal. Persist actual tool calls and measured model usage; enforce run/time limits.
- Reviewer may edit/reject/approve a proposal. Approval binds all cue IDs, asset revisions, text and timing. No agent can approve or mutate deliverables.
- Application verifies hashes and full resulting track before mutation, snapshots each asset, reindexes changed revisions and re-runs detectors via MCP before VERIFIED. Partial external failures remain pending/retryable.
- Rollback checks current versions, restores all touched assets, reindexes and rescans. Export contains tracks, version hashes, decisions and unresolved issues.
- App state survives process restart; deployment uses persistent storage. UI provides upload, spec review, findings, video evidence, readable tool trace, review, verify and export with honest error/loading states.

## Architecture / security decisions
FastAPI and React modular monolith. Transactional SQLite for local development with configurable persistent volume; production storage decision follows cloud inspection. Immutable JSON project revisions and event history, optimistic revision checks, per-project serialized writes. ClickHouse append-only indexed snapshots with a revision field; reads always filter the current revision. Official MCP via stdio with read-only credentials. Google ADK with Vertex-backed Gemini, no alternative AI providers.

Bearer reviewer token from environment for the initial single-reviewer release; server-side comparison, no role supplied by browser. Token is entered by reviewer, kept in browser memory, never bundled. All private reads and writes authenticated. Content served through authenticated fetch/object URL. Strict Pydantic models, size/type limits, no remote URL fetch on ingest, no arbitrary user SQL, generated identifiers for paths, text rendered through React escaping. Explicit read-only developer fixtures live only in tests, never successful service fallbacks.

## Completion checklist
- [ ] Real cloud/MCP connections and pinned dependencies
- [ ] Durable project, asset, spec, finding and approval models
- [ ] Ingestion and five detector classes
- [ ] Gemini extraction and ADK investigation
- [ ] Versioned approval/apply/reverify/rollback/export
- [ ] Complete review UI
- [ ] Known-answer, adversarial, integration and browser checks
- [ ] Original media fixture and honest evaluation report
- [ ] Deployment, license, README and submission materials

Security checklist reviewed before implementation: authentication/authorization are server-side; all uploads and mutations validate schemas; analytical reads are constrained and database read-only; credentials excluded from responses; mutation history persists; expensive run endpoints bounded.
