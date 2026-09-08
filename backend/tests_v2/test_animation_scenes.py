"""Independent known-answer controls from the two original animated films."""
import json
from pathlib import Path
import pytest
from backend.app.domain import Asset, Project, StorySpec
from backend.app.detectors import scan

@pytest.mark.parametrize('scene,expected',[('lantern',{'NUMBER','REVEAL','SOUND','DIALOGUE','CLUE'}),('harbor',{'NUMBER','DIALOGUE'})])
def test_original_animation_defects_and_clean_controls(scene,expected):
    root=Path(__file__).resolve().parents[2]/'demo'/scene
    spec=StorySpec.model_validate(json.loads((root/'reviewed-story-notes.json').read_text(encoding='utf-8')))
    for filename, kinds in [('clean-tracks.json',set()),('test-tracks.json',expected)]:
        assets=[Asset.model_validate(a) for a in json.loads((root/filename).read_text(encoding='utf-8'))]
        p=Project(title=scene,script=(root/'script.txt').read_text(encoding='utf-8'),assets=assets,spec=spec)
        findings=scan(p)
        assert {f.kind for f in findings}==kinds
        assert len(findings)==len(kinds)
