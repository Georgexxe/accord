> Superseded film choice: user requested an original animation on 8 September. The Last Lantern and Harbor Lights are being created with Google Veo, original script and soundtrack. The feature priorities below remain the implementation scope.

# Accord: animation replacement and product priorities

Research date: 8 September 2026. This is a recommendation and implementation scope, not a claim that the replacement has shipped.

## Film selection

The user wants existing, professionally animated anime-style footage inside the app, replacing Protocol Kepler-9. Do not generate substitute geometric animation or silently choose 3D animation instead of the requested 2D look.

Candidate: Morevna Episode 4, Death(Less). Official page provides English voice credits, translated subtitles, separated dub materials and a CC BY-SA 4.0 licence. The work is independent 2D anime; visual preference and scene suitability remain unconfirmed. Attribute the creators, identify modifications, and retain the applicable media licence separately from Accord's MIT source licence. Do not label this third-party film original Accord media.

Source: https://morevnaproject.org/anime/episode-4_old/

Do not publish a replacement merely by swapping master.mp4. Select a coherent 45–75 second excerpt, preserve its actual dialogue and sound, obtain matching source subtitles, create explicitly labelled test variants with a small number of deliberate defects, extract fresh story notes, verify each expected finding, and run the actual approve/apply/recheck/undo workflow. Avoid forcing Kepler's survivor count, code or reveal into an unrelated film.

## Competition constraint discovered

Official rules allow authorised third-party integrations, but their video requirements also say the submission must be an original unpublished work that does not incorporate third-party-owned content. An open media licence alone does not resolve this tension. Obtain organiser clarification before treating licensed existing footage as cleared for the contest submission. Do not contact organisers without user authorisation. Keep the working original demo available meanwhile.

The rules require a publicly visible YouTube or Vimeo walkthrough of no more than three minutes (only the first three minutes evaluated if longer). GitHub-hosted MP4 is an additional download, not fulfillment of the specified host requirement. Existing v2.1.0 is not claimed as a completed contest submission.

Source: https://agentic-cinema.devpost.com/rules

## Product priorities after reviewing original plan and current source

The original research and completion contract already cover extraction, five issue classes, ClickHouse MCP investigation, explicit approval, bounded repair, verification, export and rollback. Improve the experience and demonstrated evidence around that core before expanding into other workflows.

1. Before/after playback: preview a proposed subtitle or caption over the same film moment and switch between current and proposed versions before approval. Handle INSERT and DELETE, timing changes, subtitle placement, and derivative offsets. Preserve current tracks until exact approval.
2. Friendly change editor: replace the visible JSON editing interaction with text, start/end timing and placement controls. Validate fields before save, preserve protected asset/cue IDs and base hashes, and use the existing proposal validation and approval digest. Show original and proposed content for review.
3. Linked-version impact view: show which subtitle, recap and trailer share an affected cue, their current findings and what the proposal actually changes. Derive the display from real project lineage and proposal records; do not imply every downstream asset is corrected automatically.
4. Evidence pass: run on the new real animation excerpt and a second distinct scene, with clean controls as well as injected defects. Report misses and false positives, separate deterministic checks from model judgments, and avoid presenting seeded-demo results as general translation accuracy.

Judging criteria are equally weighted: technological implementation, design, potential impact and quality of idea. The above priorities improve inspectability and coherence, while keeping Google/ClickHouse use central. They cannot guarantee a prize.

## Capture notes

Self-hosted Firecrawl health passed. Both animation discovery searches returned success with empty results, so ordinary web search supplemented discovery. Official contest rules and Morevna page were captured under .firecrawl/accord-animation. A web fetch of Blender Studio Charge and Sintel About failed with HTTP 402; those were not used as verified replacement recommendations.
