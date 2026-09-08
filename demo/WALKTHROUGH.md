# Walkthrough transcript

Actual hosted UI; edited waiting time; original synthetic source scene. Narration generated with Google Cloud Text-to-Speech.

## 01-sources

Every audience should get the same story. StoryParity reviews what changed between a master and its localized and accessible versions. This original synthetic scene has six tracks: Spanish subtitles, English captions, audio description, a dub transcript, and linked Spanish recap and trailer versions.

## 02-spec

Gemini on Google Cloud analyzes the master video, audio, and script. Its candidate specification includes story facts, identity reveals, important sounds, dialogue intervals, and on-screen clues. A reviewer checks and edits those facts before approving the exact version. In this acceptance run, measured source annotations corrected dialogue timing.

## 03-findings

The approved specification drives bounded checks against actual versioned tracks. The evidence player links each finding to the master timeline and previews the selected subtitle text and placement. These are review candidates with visible evidence, not a general claim that artificial intelligence can certify a translation.

## 04-defects

Here, fourteen survivors became four, including in the linked recap and trailer. A name appears too early. Captions omit the critical door-lock sound. Audio description overlaps dialogue, and a subtitle covers the access code. All five supported defect classes are present in this deliberately defective test scene.

## 05-proposal

A real Google ADK investigator reads approved evidence and current versions through the official ClickHouse MCP server. Google embeddings rank related cues. The agent proposes exact multi-asset changes. In this demonstration, the test reviewer corrected caption wording and placement before approving. The model cannot authorize its own repair.

## 06-verified

After approval, the server checks the specification, exact cue identifiers, base hashes, timing, and placement. It snapshots affected assets, applies the changes, reindexes them, and reads them back through MCP. Verified means the current configured checks passed. The delivery export includes corrected tracks and a versioned report.

## 07-evidence

The activity view preserves approval decisions, actual tool queries, and measured model usage. Cloud state is durable in Firestore and private Cloud Storage. Application data requires the reviewer key. The source, original test inputs, and reproducible validation runners are published with the release.

## 08-rollback

Rollback checks for later edits before restoring every affected asset and repeating the checks. The original findings return, including the linked derivatives. This edited walkthrough shows real hosted application states; waiting time is omitted. AI investigates. People approve. Checks verify.
