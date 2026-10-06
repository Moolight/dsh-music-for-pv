"""Print duration / sample rate / channels for a set of audio files.

    python audio_info.py song.flac other.wav
    python audio_info.py input/*.flac
"""
import os
import sys

import soundfile as sf

paths = sys.argv[1:]
if not paths:
    sys.exit(__doc__)

for p in paths:
    try:
        info = sf.info(p)
        print("%7.2fs  %d Hz  %d ch  %-9s  %s" % (
            info.duration, info.samplerate, info.channels, info.subtype,
            os.path.basename(p)[:60]))
    except Exception as e:
        print("  ERR", os.path.basename(p), e)
