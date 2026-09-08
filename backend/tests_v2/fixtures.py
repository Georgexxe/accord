"""Explicit synthetic known-answer examples, never represented as model output."""
from backend.app.domain import Asset, Box, Cue, Invariant, Project, StorySpec


def make_project(*, clean=False):
    """Five independent planted defects or their corrected clean control."""
    spec = StorySpec(notes="SYNTHETIC TEST SPECIFICATION: human authored; not Gemini extraction.", invariants=[
        Invariant(id="fact", kind="NUMBER", description="Survivor count", start=10, end=14,
                  value="14", evidence="Synthetic script: There are 14 survivors."),
        Invariant(id="identity", kind="REVEAL", description="Identity revealed at 30s", start=30, end=34,
                  value="Mara", aliases=["Captain Mara"], evidence="Synthetic script reveals Mara at 30s."),
        Invariant(id="alarm", kind="SOUND", description="Warning signal", start=20, end=23,
                  value="alarm", aliases=["siren"], evidence="Synthetic script: alarm sounds at 20s."),
        Invariant(id="speech", kind="DIALOGUE", description="Critical dialogue", start=40, end=44,
                  value="Do not open it", evidence="Synthetic script: Do not open it, 40-44s."),
        Invariant(id="code", kind="CLUE", description="Visible access code", start=50, end=54,
                  value="access code", evidence="Synthetic storyboard places the access code in lower frame.",
                  box=Box(x=.3, y=.7, width=.4, height=.15)),
    ])
    assets = [
        Asset(id="es-episode", name="Synthetic Spanish episode", locale="es", kind="SUBTITLE", cues=[
            Cue(id="number", start=10, end=14, text="Hay 14 supervivientes." if clean else "Hay 114 supervivientes."),
            Cue(id="reveal", start=30 if clean else 25, end=34 if clean else 29, text="Mara está aquí."),
            Cue(id="clue", start=50, end=54, text="La puerta está cerrada.",
                box=Box(x=.3, y=.1 if clean else .7, width=.4, height=.15)),
        ]),
        Asset(id="en-sdh", name="Synthetic English SDH", locale="en", kind="SDH", cues=[
            Cue(id="sound", start=20, end=23, text="[alarm sounds]" if clean else "[wind blows]"),
        ]),
        Asset(id="en-ad", name="Synthetic English AD", locale="en", kind="AD", cues=[
            Cue(id="description", start=44 if clean else 41, end=47 if clean else 44,
                text="She reaches for the door."),
        ]),
    ]
    project = Project(id="synthetic-demo", title="Synthetic StoryParity known-answer demo",
                      script="SYNTHETIC TEST SCRIPT. 10s: There are 14 survivors. 20s: alarm sounds. "
                             "30s: Mara's identity is revealed. 40-44s: Do not open it. 50s: access code visible.",
                      assets=assets, spec=spec)
    project.record("SYNTHETIC_FIXTURE_CREATED", actor="test-fixture", source="Human-authored known-answer data; no model call")
    return project
