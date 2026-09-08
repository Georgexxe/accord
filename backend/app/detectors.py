"""Evidence-based deterministic checks. Semantic candidates require Gemini review."""
import re
from .domain import Asset, Finding, Project


def overlap(a, b, c, d):
    return max(0.0, min(b, d) - max(a, c))


def numbers(text):
    # Thousands separators are normalized; decimals are preserved.
    normalized = re.sub(r"(?<=\d)[, .](?=\d{3}(?:\D|$))", "", text)
    return re.findall(r"(?<!\w)\d+(?:[.,]\d+)?(?!\w)", normalized)


def scan(project: Project) -> list[Finding]:
    if not project.spec:
        raise ValueError("Approve a story specification before scanning")
    result = []
    for asset in project.assets:
        for inv in project.spec.invariants:
            matching = [c for c in asset.cues if overlap(c.start + asset.master_offset, c.end + asset.master_offset, inv.start, inv.end)]
            def report(cue, message, severity="ERROR"):
                result.append(Finding(asset_id=asset.id, cue_id=cue.id if cue else None,
                    invariant_id=inv.id, kind=inv.kind, description=message, evidence=inv.evidence,
                    start=cue.start if cue else max(0, inv.start-asset.master_offset),
                    end=cue.end if cue else max(.01, inv.end-asset.master_offset), severity=severity))
            if inv.kind == "NUMBER" and asset.kind in {"SUBTITLE", "DUB", "SDH"}:
                expected = numbers(inv.value)
                for cue in matching:
                    observed = numbers(cue.text)
                    if expected and observed and not set(expected).issubset(observed):
                        report(cue, f"Expected numeric fact {inv.value}; observed {', '.join(observed)}. Confirm the aligned dialogue refers to this fact.", "REVIEW")
            elif inv.kind == "REVEAL":
                names = [inv.value, *inv.aliases]
                for cue in asset.cues:
                    if cue.start + asset.master_offset < inv.start and any(re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", cue.text, re.I) for n in names if n):
                        report(cue, f"'{inv.value}' appears before the approved reveal at {inv.start:.2f}s")
            elif inv.kind == "SOUND" and asset.kind == "SDH":
                coverage_start = min(c.start for c in asset.cues) + asset.master_offset
                coverage_end = max(c.end for c in asset.cues) + asset.master_offset
                if not overlap(coverage_start, coverage_end, inv.start, inv.end):
                    continue
                aliases = [inv.value, *inv.aliases]
                if not any(any(a.casefold() in c.text.casefold() for a in aliases if a) for c in matching):
                    report(None, f"No matching SDH cue for plot-critical sound '{inv.value}'. Review equivalent wording.", "REVIEW")
            elif inv.kind == "DIALOGUE" and asset.kind == "AD":
                for cue in matching:
                    seconds = overlap(cue.start+asset.master_offset, cue.end+asset.master_offset, inv.start, inv.end)
                    report(cue, f"Audio description overlaps approved dialogue by {seconds:.2f}s")
            elif inv.kind == "CLUE" and inv.box and asset.kind in {"SUBTITLE", "SDH"}:
                for cue in matching:
                    if cue.box and overlap(cue.box.x, cue.box.x+cue.box.width, inv.box.x, inv.box.x+inv.box.width) and overlap(cue.box.y, cue.box.y+cue.box.height, inv.box.y, inv.box.y+inv.box.height):
                        report(cue, "Subtitle placement overlaps the approved on-screen clue region")
    return result
