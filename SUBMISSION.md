# StoryParity

**Every audience gets the same story.**

A localized subtitle can turn fourteen survivors into four. A trailer can reveal an identity too early. Missing sound captions, overlapping audio description or a subtitle covering a vital code can change the story another audience experiences. These defects travel into downstream edits and are difficult to audit as isolated files.

StoryParity ties versions to a human-approved, timecoded specification extracted from the master by Vertex Gemini. It indexes tracks and lineage in ClickHouse, gathers evidence through the official ClickHouse MCP server, and uses a Google ADK investigator to propose bounded repairs. Google multilingual embeddings rank candidate evidence. The reviewer owns the exact change; the application applies it only against the approved specification and unchanged base hashes, then reindexes and verifies. Rollback restores all affected versions and export includes the audit trail.

## Demonstration

Use `demo/master.mp4`, `demo/master-script.txt` and the four supplied JSON tracks. Add Spanish recap and trailer tracks with a cue reading `Hay 4 supervivientes.` mapped to master seconds 10–14; link their parent to the Spanish subtitle track. Extract and inspect the story specification, approve it, and run checks. Inspect the five defect classes and linked derivative findings. Investigate, review each exact proposal, approve, verify, export and roll back.

Suggested three-minute narration:

1. **0:00–0:25:** Play the master and show the six-version inventory. Explain how one story fact changed across localized and derivative tracks.
2. **0:25–0:55:** Show Gemini's timecoded specification and the explicit reviewer approval gate.
3. **0:55–1:25:** Show numeric, reveal, SDH, AD and visual-clue findings. Seek the master to the evidence.
4. **1:25–2:10:** Show actual ADK/MCP tool evidence and the multi-asset repair diff. Explain that semantic similarity ranks evidence; it does not authorize changes.
5. **2:10–2:40:** Approve exact changes, show VERIFIED after actual reindex/readback and download the versioned export.
6. **2:40–3:00:** Roll back and show restored findings. Close with “AI investigates. People approve. Checks verify.”

Any edited recording must label omitted wait time and synthetic source media. Do not present scripted inputs as model output or general accuracy results.

## Build

React/TypeScript, FastAPI/Pydantic, Google ADK, Vertex Gemini, Google embeddings, official `mcp-clickhouse`, ClickHouse, Firestore, private Cloud Storage, Secret Manager and Cloud Run. Original demo speech uses Google Cloud Text-to-Speech. MIT license. See README for architecture and `VALIDATION.md` for measured evidence and limits.

Public application, source repository and video links will be filled after publication approval. Staging is IAM-private and also requires the reviewer key.
