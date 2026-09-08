import pytest

from backend.app.validators.parsers import parse_srt, parse_vtt, serialize_srt


def test_srt_bom_crlf_multiline_and_roundtrip_are_preserved():
    raw = "\ufeff1\r\n00:00:10,000 --> 00:00:14,000\r\nMARIA: Primera línea\r\nSegunda línea\r\n"
    cues = parse_srt(raw)
    assert len(cues) == 1
    assert cues[0].text == "MARIA: Primera línea\nSegunda línea"
    assert cues[0].speaker == "MARIA"
    assert parse_srt(serialize_srt(cues)) == cues


def test_vtt_identifiers_settings_and_non_cue_blocks_are_supported():
    raw = "WEBVTT\n\nNOTE human-authored note\nNot a cue\n\nSTYLE\n::cue { color: white; }\n\nscene-opening\n00:10.000 --> 00:14.000 align:start position:20%\nHello\n"
    cues = parse_vtt(raw)
    assert [(c.index, c.start_seconds, c.end_seconds, c.text) for c in cues] == [(1, 10, 14, "Hello")]


@pytest.mark.parametrize("raw", [
    "WEBVTT\n\n00:10.000 -->\nMissing end\n",
    "WEBVTT\n\n00:10.000 --> 00:09.000\nReversed\n",
    "WEBVTT\n\n00:99.000 --> 01:00.000\nInvalid seconds\n",
])
def test_bad_vtt_times_produce_validation_error(raw):
    with pytest.raises(ValueError):
        parse_vtt(raw)
