# Accord

**Keep the story intact across every version.**

A localized subtitle can turn fourteen passengers into four. A trailer can reveal an identity too early. Missing sound captions, overlapping audio description or a subtitle covering a platform sign can change the story another audience experiences. These defects travel into downstream edits and are difficult to audit as isolated files.

Accord ties versions to a human-approved, timecoded specification extracted from the master by Vertex Gemini. It indexes tracks and lineage in ClickHouse, gathers evidence through the official ClickHouse MCP server, and uses a Google ADK investigator to propose bounded repairs. Google multilingual embeddings rank candidate evidence. The reviewer owns the exact change; the application applies it only against the approved specification and unchanged base hashes, then reindexes and verifies. Rollback restores all affected versions and export includes the audit trail.

## Demonstration

The main demonstration is **The Last Lantern**, a 48-second original AI-assisted animated short in `demo/lantern/master.mp4`. A courier carries a lantern to fourteen passengers waiting at a mountain station. Use the accompanying script and test tracks, including intentionally incorrect passenger counts, an early identity reveal, a missing warning bell, overlapping audio description and a subtitle covering the platform sign. Linked Spanish recap and trailer tracks carry the passenger-count defect into two derivative versions. The separate 16-second **Harbor Lights** scene in `demo/harbor` tests a different number fact and dialogue overlap.

Extract and review the story notes, approve the reference, and run checks. Preview proposed captions over the actual film, edit text, timing and placement with ordinary controls, then approve, verify, export and undo. These samples use original scripts, Google Veo imagery, Google speech and synthesized sound; see `demo/ANIMATION-PROVENANCE.md`. The earlier geometric scene remains only as a historical fixture.

The walkthrough follows the original film, approved story notes, seven findings, Before/After preview, ordinary caption editing, verified delivery, history and Undo. It is less than three minutes.

Any edited recording must label omitted wait time and synthetic source media. Do not present scripted inputs as model output or general accuracy results.

## Build

React/TypeScript, FastAPI/Pydantic, Google ADK, Vertex Gemini, Google embeddings, official `mcp-clickhouse`, ClickHouse, Firestore, private Cloud Storage, Secret Manager and Cloud Run. Original demo speech uses Google Cloud Text-to-Speech. MIT license. See README for architecture and `VALIDATION.md` for measured evidence and limits.

Application: [Accord review studio](https://storyparity-cus2bs7tpq-uc.a.run.app). Project data requires the private reviewer key.

Source: [Georgexxe/accord](https://github.com/Georgexxe/accord), MIT licensed.

Public demo video: [Accord walkthrough — 1:56](https://github.com/Georgexxe/accord/releases/download/v2.2.0/Accord-walkthrough.mp4). [Release page](https://github.com/Georgexxe/accord/releases/tag/v2.2.0).

The edited walkthrough uses actual hosted application screens and Google Cloud narration. It includes explicit test-reviewer edits and labels omitted wait time. The original demo is loaded in production. Staging remains IAM-private.

## Submission status

YouTube/Vimeo publication is pending: the signed-in YouTube Studio browser connection could not be controlled reliably. The GitHub video download is available with the release, but does not replace the competition-required streaming-platform URL. Upload metadata is prepared in `demo/YOUTUBE-UPLOAD.md`. No competition entry has been submitted.
