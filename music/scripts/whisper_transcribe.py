"""Transcribe a song with faster-whisper and dump word-level timestamps.

usage: whisper_transcribe.py <audio> [--model small] [--out words.json]
                             [--highpass 140] [--no-vad]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sandbox_patch  # noqa: F401  (patches tempfile before any library uses it)

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--model", default="small")
    ap.add_argument("--model-path", default="",
                    help="local CTranslate2 model directory (skips the HF hub cache)")
    ap.add_argument("--out", default="")
    ap.add_argument("--highpass", type=float, default=140.0)
    ap.add_argument("--no-vad", action="store_true")
    ap.add_argument("--language", default="en", help="en, zh, ja, ...")
    ap.add_argument("--prompt-from", default="",
                    help="lyrics file; its first --prompt-lines lines seed initial_prompt")
    ap.add_argument("--prompt-lines", type=int, default=24,
                    help="Whisper's prompt window is ~224 tokens, so only a slice fits")
    args = ap.parse_args()

    wav, sr = sf.read(args.audio, dtype="float32", always_2d=True)
    wav = wav.mean(axis=1)
    if args.highpass > 0:
        import torch
        import torchaudio
        t = torchaudio.functional.highpass_biquad(torch.from_numpy(wav), sr, args.highpass)
        wav = t.numpy()
    if sr != 16000:
        import torch
        import torchaudio
        wav = torchaudio.functional.resample(torch.from_numpy(wav), sr, 16000).numpy()
    audio = np.ascontiguousarray(wav, dtype=np.float32)

    prompt = None
    if args.prompt_from:
        import re as _re
        kept = []
        for raw in open(args.prompt_from, encoding="utf-8"):
            s = raw.strip()
            if s and not _re.match(r"^\[[^\]]+\]$", s):
                kept.append(s)
        prompt = " ".join(kept[:args.prompt_lines])
        print("initial_prompt: %d lines, %d chars" % (args.prompt_lines, len(prompt)))

    target = args.model_path or args.model
    model = WhisperModel(target, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        audio,
        language=args.language,
        beam_size=5,
        word_timestamps=True,
        vad_filter=not args.no_vad,
        initial_prompt=prompt,
        condition_on_previous_text=False,
    )
    print("model=%s  lang=%s (p=%.2f)  duration=%.1fs" %
          (target, info.language, info.language_probability, info.duration))
    print("-" * 70)

    words, segs = [], []
    for seg in segments:
        segs.append({"start": seg.start, "end": seg.end, "text": seg.text.strip()})
        print("[%6.2f -> %6.2f] %s" % (seg.start, seg.end, seg.text.strip()))
        for w in (seg.words or []):
            words.append({"start": w.start, "end": w.end, "word": w.word})

    print("-" * 70)
    print("segments: %d   words: %d" % (len(segs), len(words)))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"model": args.model, "segments": segs, "words": words},
                      fh, ensure_ascii=False, indent=1)
        print("wrote", args.out)


if __name__ == "__main__":
    sys.exit(main())
