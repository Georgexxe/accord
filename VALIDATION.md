# StoryParity validation record

Date: 8 September 2026. These are measured acceptance results on bounded synthetic inputs, not population-level accuracy claims.

## Reproducible checks

- Python: **61 passed**, using `python -m pytest -q` against the active `backend/tests_v2` suite, including complete/incomplete/stale proposal previews with full state immutability assertions.
- Scope: five known-answer detector classes and clean controls, persistent state, stale revisions, spec/proposal tampering, exact cue IDs, multi-asset repair and rollback, authorization, failed cloud operations and verification recovery.
- Parser regressions: malformed timestamps/blocks rejected; millisecond rounding carries into the next minute/hour; BOM, CRLF, multiline SRT, WebVTT named cues/settings/notes supported.
- Browser: desktop and 390-pixel mobile checks passed with no JavaScript errors or horizontal body overflow. Evidence player seek/overlay checks used explicitly labelled synthetic browser interception; these are UI tests, not live cloud evidence.

## Actual service evidence

The dedicated ClickHouse instance reported version 26.3.12.3. The reader account returned `readonly=1`. Official `mcp-clickhouse` 0.6.0 `run_query` executed an impossible predicate and returned zero rows. Vertex Gemini extracted candidate invariants from the original video/audio; Google ADK called actual MCP evidence tools. Actual `gemini-embedding-001` vectors were ranked using ClickHouse `cosineDistance` through MCP.

The first full live run used the 60-second original synthetic scene and four tracks. It detected seven findings across NUMBER, REVEAL, SOUND, DIALOGUE and CLUE. A test reviewer approved the exact extracted spec and actual model proposal; apply/reindex/MCP readback returned VERIFIED with zero remaining findings. Export contained four SRT tracks. Rollback restored seven findings. Firestore, private Cloud Storage, Vertex and ClickHouse were real services. This automated acceptance reviewer is not a professional linguistic evaluation.

The separate live semantic investigation passed with seven proposed changes, actual semantic tool use and five recorded trace events. Service output, SQL, actual usage metadata and proposal JSON are retained privately under `runtime/`; credentials are excluded. The public source includes runners and original inputs, not private account data.

## Hosted release gate

Six-track remote acceptance includes parent-linked recap and trailer tracks. The first hosted pass exposed a rounded dialogue boundary in the raw extraction. The test reviewer replaced dialogue intervals with measured synthetic-source annotations and approved the proper-name alias Mara. An initial proposed SDH insertion exceeded the configured reading speed and was rejected before mutation. A later short equivalent caption remained a REVIEW item because the approved aliases did not include that wording; the test reviewer explicitly approved `door locks, beeps`. Raw model output remains separate from these reference-review decisions.

The agent now has a read-only preview tool that checks an isolated candidate for presentation errors and remaining configured findings. It never saves, applies, approves, or claims an MCP-verified result.

**Final hosted acceptance: PASS.** On staging revision `storyparity-staging-00004-rdq`, six uploaded tracks produced seven findings across all five classes. The actual ADK run used the approved-spec tool, two official MCP queries (including semantic distance), and a candidate preview reporting zero remaining findings; three model usage events were recorded. Seven exact changes were approved by the synthetic test reviewer. Live reindex/MCP readback returned VERIFIED with zero findings. Export contained six SRT tracks. Rollback restored seven findings and the original defective text in both linked derivatives. Evidence is retained under `runtime/hosted-delivery/`.

The first rejected/incomplete runs above are retained as useful limitations, not omitted from the measured record. Passing required explicit reference-review decisions; this is not a claim of unattended end-to-end linguistic correctness.

A production repeat again produced a reasonable but unapproved sound synonym and an overlapping placement suggestion. Candidate preview and live verification reported both; the application never falsely marked that delivery VERIFIED. The production demonstration therefore includes explicit test-reviewer edits to use the approved sound caption and a clear placement region before exact approval. This illustrates why proposal editing and re-verification remain part of the product.

**Production demonstration: PASS.** On revision `storyparity-00002-r2p`, the reviewed seven-change proposal returned VERIFIED with zero findings, and rollback restored seven findings. Eight actual hosted desktop screens were captured across sources, spec, findings, proposal, verified delivery, evidence and rollback. Browser phases reported zero JavaScript errors; all four 390-pixel mobile checks had no horizontal body overflow. No response interception was used for these production captures. The original demo remains in the application with restored defects so reviewers can exercise the workflow.

The public walkthrough is 167.375 seconds (2:47), 1440×1080 H.264 with AAC narration, approximately 3.81 MB. Full FFmpeg decoding completed without errors. The transcript is included in `demo/WALKTHROUGH.md`; actual hosted screens, synthetic source media and omitted waiting time are labelled.

## Practical limits

Numeric checks recognize digits, not every written number in every language. Sound equivalence depends on approved aliases. A missing or incorrect approved fact limits all downstream checks. Placement checks require supplied boxes. Linear timeline offsets support trims; montage segments require separate mappings. VERIFIED means the current configured checks passed, not that the film is certified accessible or perfectly translated.

Single-reviewer bearer authentication and a single persistent ClickHouse VM suit this release; multi-tenant access, high availability and broad human-labelled multilingual benchmarks remain future work. Cloud charges continue until resources are stopped or removed; see deployment instructions.

## Accord branding and interface update

The application now uses Accord throughout its customer interface, page metadata and delivery exports. The welcome screen, labels and prompts were simplified; detailed diagnostics remain in project history. The renamed repository is https://github.com/Georgexxe/accord. Existing infrastructure identifiers remain compatible.

All 61 backend tests passed. Desktop/mobile sign-in checks passed with no JavaScript errors or horizontal overflow. Fresh production captures verify the reviewed repair and rollback with the rebranded original film; its audio and story timecodes were retained. The replacement walkthrough is 1:59 (119.374 seconds), uses nine fresh hosted screens and new narration, and decodes completely without errors. Earlier evidence above describes the prior release.
