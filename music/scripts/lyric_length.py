"""Report lyric length per section.

YuE2's free (no-ABC) generation decides the song length from how much lyrics it
is given, so this is the knob that controls duration: roughly 2 syllables per
second of singing here, plus an intro and outro. Section tags must be the ones
YuE2 knows -- [Verse] [Chorus] [Bridge] [Outro] -- or the block is ignored.

usage: lyric_length.py <lyrics.txt>
"""
import re
import sys

TAG = re.compile(r"^\[(.+)\]$")
KEEP = re.compile(r"[^\w]", re.UNICODE)
CJK = re.compile(r"[\u3400-\u9fff\u3040-\u30ff]")


def sing_rate(path):
    """Seconds of singing per syllable, measured on the two Chinese renders.

    Chinese packs roughly twice the syllables per second of English, so a single
    rate would mis-estimate badly. These are the observed YuE2 numbers.
    """
    text = open(path, encoding="utf-8").read()
    cjk = len(CJK.findall(text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return 3.9 if cjk > latin else 1.8


def main():
    path = sys.argv[1]
    blocks = []
    cur = None
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if not line:
            continue
        m = TAG.match(line)
        if m:
            cur = [m.group(1), 0, 0]
            blocks.append(cur)
            continue
        n = len(KEEP.sub("", line))
        if cur is not None:
            cur[1] += 1
            cur[2] += n

    std = {"verse", "chorus", "bridge", "outro", "intro"}
    total_l = total_c = 0
    print("%-12s %7s %7s  %s" % ("section", "lines", "chars", "tag ok?"))
    print("-" * 40)
    for name, cnt, chars in blocks:
        ok = "yes" if name.strip().lower() in std else "NO -- YuE2 ignores it"
        print("%-12s %7d %7d  %s" % (name, cnt, chars, ok))
        total_l += cnt
        total_c += chars
    print("-" * 40)
    print("%-12s %7d %7d" % ("TOTAL", total_l, total_c))
    print()
    rate = sing_rate(path)
    est = total_c / rate + 12          # allow a little intro/outro
    print("measured pace ~%.1f syllables/s -> about %d:%02d" % (rate, est // 60, est % 60))


if __name__ == "__main__":
    sys.exit(main())
