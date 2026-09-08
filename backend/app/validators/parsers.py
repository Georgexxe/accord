"""Strict SRT/WebVTT parsing and millisecond-safe serialization."""
import math
import re
from dataclasses import dataclass

@dataclass
class ParsedCue:
    index: int
    start_time: str
    end_time: str
    start_seconds: float
    end_seconds: float
    text: str
    speaker: str = ''
    lines: list[str] | None = None
    def __post_init__(self):
        if self.lines is None: self.lines=self.text.split('\n')

def parse_timecode_to_seconds(tc: str) -> float:
    match=re.fullmatch(r'(?:(\d{2,3}):)?([0-5]\d):([0-5]\d)[,.](\d{3})',tc.strip())
    if not match: raise ValueError(f'Malformed timestamp: {tc!r}')
    hour,minute,second,millis=match.groups()
    return int(hour or 0)*3600+int(minute)*60+int(second)+int(millis)/1000

def seconds_to_srt_timecode(sec: float) -> str:
    if not math.isfinite(sec) or sec<0: raise ValueError('Timestamp must be finite and nonnegative')
    total=round(sec*1000)
    hours,total=divmod(total,3600000);minutes,total=divmod(total,60000);seconds,millis=divmod(total,1000)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}'

def seconds_to_vtt_timecode(sec): return seconds_to_srt_timecode(sec).replace(',','.')

def _blocks(content, vtt=False):
    content=content.lstrip('\ufeff').replace('\r\n','\n').replace('\r','\n').strip()
    if not content: return []
    blocks=re.split(r'\n\s*\n',content)
    if vtt:
        if not blocks[0].startswith('WEBVTT'): raise ValueError('WebVTT must start with WEBVTT header')
        blocks=blocks[1:]
    cues=[]
    for block in blocks:
        lines=block.splitlines()
        if vtt and (lines[0].startswith('NOTE') or lines[0] in {'STYLE','REGION'}): continue
        if '-->' in lines[0]:
            if not vtt: raise ValueError('SRT cue must start with a numeric ID')
            idx=len(cues)+1;timing=lines[0];body=lines[1:]
        else:
            if len(lines)<3: raise ValueError('Incomplete subtitle cue block')
            if not vtt and not lines[0].strip().isdigit(): raise ValueError('SRT cue ID must be numeric')
            idx=int(lines[0]) if lines[0].strip().isdigit() else len(cues)+1
            timing=lines[1];body=lines[2:]
        parts=timing.split('-->')
        if len(parts)!=2 or not body or not any(x.strip() for x in body): raise ValueError('Malformed or empty subtitle cue')
        start=parts[0].strip();end=parts[1].strip()
        if vtt:
            if not end.split(): raise ValueError('Missing subtitle end timestamp')
            end=end.split()[0]
        start_seconds=parse_timecode_to_seconds(start);end_seconds=parse_timecode_to_seconds(end)
        if end_seconds<=start_seconds: raise ValueError('Subtitle end must follow start')
        text='\n'.join(body)
        speaker_match=re.match(r'^\[?([A-Z0-9 _.-]+?)\]?\s*:',text)
        cues.append(ParsedCue(idx,start,end,start_seconds,end_seconds,text,speaker_match.group(1) if speaker_match else '',body))
    if len({c.index for c in cues})!=len(cues): raise ValueError('Duplicate subtitle cue ID')
    return cues

def parse_srt(content): return _blocks(content)
def parse_vtt(content): return _blocks(content,True)
def serialize_srt(cues):
    return '\n\n'.join(f'{c.index}\n{seconds_to_srt_timecode(c.start_seconds)} --> {seconds_to_srt_timecode(c.end_seconds)}\n{c.text}' for c in cues)+'\n'
