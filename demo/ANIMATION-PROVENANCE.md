# Original animation production

Accord's primary sample is **The Last Lantern**, a 48-second fictional short. A courier brings a lantern to a mountain railway station, where fourteen passengers need a signal to reach home. A separate 16-second lighthouse scene, **Harbor Lights**, tests different material.

The story, dialogue, shot directions, edit and sound design were created for this project. Moving images were generated with Google Cloud Veo `veo-3.1-fast-generate-001`; the original script is voiced by Google Cloud Text-to-Speech (`en-US-Standard-F` and `en-US-Standard-D`). Rain, musical tones and bell sounds are synthesized by `scripts/assemble_lantern.py`. The platform sign and opening title are composited during editing. The films contain no extracted footage, music or characters from an existing anime.

These are AI-assisted animations, not claimed as traditionally hand-animated works. Voice delivery is composed over the shots; it is not a claim of frame-perfect dialogue lip synchronization. Generated character details can vary between shots.

Reproduction:

1. Install the backend requirements and `scripts/requirements-demo.txt`; install FFmpeg and authenticate the Google Cloud CLI to an authorised billed project.
2. Run `python scripts/animate_lantern.py --gcloud PATH --shots 0,1,2,3,4,5,6,7`. Generation prompts are in the script. Saved operations allow resuming without resubmitting completed requests. Google Cloud usage is chargeable.
3. Run `python scripts/assemble_lantern.py --gcloud PATH` and `python scripts/build_animation_demo.py`.
4. The finished films and known-answer test packages are in `demo/lantern/` and `demo/harbor/`. Actual generation is nondeterministic; regenerated artwork may differ. Reinspect regenerated films, sound and timecodes before reusing their story references.

`test-tracks.json` deliberately introduces defects. `clean-tracks.json` is the control. Reviewed story notes are explicit evaluation references; actual Gemini extraction outputs and ADK/MCP acceptance results are retained separately during runs. Human corrections to model proposals are recorded as reviewer edits, not model output.

The earlier `demo/master.mp4` is the historical procedural Kepler test scene. It remains for reproducibility and is superseded as the primary sample.
