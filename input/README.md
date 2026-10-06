# Put your own copies here

This folder is gitignored — nothing in it is redistributed with the code. The
pipeline expects these four names by default; point `PV_SONG`, `PV_LYRICS`,
`PV_LRC` and `PV_WHISPER` somewhere else if you prefer.

| file | what it is | where it comes from |
|---|---|---|
| `song.flac` | the rendered song | anything: your own recording, a model, a DAW |
| `lyrics.txt` | the lyric sheet, one sung line per line, `[Verse]`/`[Chorus]`/`[Bridge]`/`[Outro]` section tags | you write it |
| `lyrics.lrc` | the same lines with `[mm:ss.cc]` timestamps | an LRC editor, or your DAW's markers |
| `whisper_words.json` | word-level timestamps | run Whisper over the song |

`timeline.py` merges the last three into `out/timeline.json`, which is what the
renderer reads.

## The whisper file

Any tool that emits this shape will do:

```json
{
  "segments": [{"start": 0.0, "end": 2.4, "text": "…"}],
  "words":    [{"start": 0.0, "end": 0.42, "word": "…"}]
}
```

faster-whisper with `word_timestamps=True` produces it. **Do not enable VAD** —
on a sung track it swallows whole sections and the timings for everything after
the gap are wrong.

## If your song is not in Chinese

The lyric band highlights characters by spreading Whisper's word timings across
the line (see `pv.py:char_times`). It matches positionally rather than by
character, because a Chinese ASR mostly returns homophones and traditional forms
— that also makes it work unchanged for Latin lyrics.

## If you only want the film, not your own song

Nothing here is required to read the code, and the film itself is not in the
repository (see the top-level README). The four files above are what you need to
render it.
