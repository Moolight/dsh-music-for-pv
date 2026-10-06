"""Build an LRC from Whisper timestamps, monotonic-DP matched to the known lyrics.

Why not CTC forced alignment: the lyric set repeats heavily (Intro and Verse 1 are
the same four lines, the Chorus appears three times). CTC alignment can lock a
repeated block onto the wrong repetition and then every later line is off by tens
of seconds -- while still reporting zero inversions, so the failure is invisible.

Why not word-by-word matching either: common words (I'm, know, my) match spurious
places and create false anchors. This aligns whole lyric LINES to whole Whisper
PHRASES with a monotonic dynamic program scored by fuzzy similarity, so a line can
only be anchored to a phrase that actually sounds like it and that comes after the
previous line's anchor.

Lines with no phrase are interpolated between neighbours; a trailing run of lines
that never matched was simply not sung and is dropped (and reported).

usage: build_lrc_from_whisper.py --words w.json --lyrics en.txt --audio s.flac --out s.lrc
"""
import argparse
import json
import os
import re
import sys
from difflib import SequenceMatcher

SECTION_RE = re.compile(r"^\[([^\]]+)\]\s*$")
MIN_SIM = 0.42
# Chinese has no word spaces, so a lyric line is one big token to a whitespace
# splitter and the word-level refinement cannot place anything inside a merged
# Whisper segment. Splitting CJK per character fixes that.
CJK = re.compile(r"[\u3400-\u9fff\u3040-\u30ff\uff66-\uff9f]")


def split_tokens(text):
    """Latin words plus single CJK characters, in order."""
    out, buf = [], []
    for ch in text.upper():
        if CJK.match(ch):
            if buf:
                out.append("".join(buf)); buf = []
            out.append(ch)
        elif ch.isalnum() or ch == "'":
            buf.append(ch)
        else:
            if buf:
                out.append("".join(buf)); buf = []
    if buf:
        out.append("".join(buf))
    return out


def norm_text(s):
    s = re.sub(r"[^\w' ]", " ", s.upper(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip()


def norm_word(s):
    return re.sub(r"[^\w']", "", s.upper(), flags=re.UNICODE)


_PY = {}


def pinyin_text(s):
    """Pinyin for CJK text, so a homophone Whisper heard still matches.

    Whisper sings back "挽着雨才伤败" for "摸完这鱼再上班" -- 鱼/雨 and 上/伤 are
    the same syllable. Comparing characters scores that near zero and the line
    loses its anchor; comparing pinyin scores it high and the anchor survives.
    """
    if not s:
        return ""
    if s in _PY:
        return _PY[s]
    try:
        from pypinyin import lazy_pinyin
        out = "".join(lazy_pinyin(s))
    except Exception:
        out = s
    _PY[s] = out
    return out


def tok_key(t):
    return pinyin_text(t) if CJK.match(t) else t


def tokens_of(line):
    """Keys, not raw text: homophones compare equal from here on."""
    return [tok_key(t) for t in split_tokens(line)]


def find_tokens(words, toks, start=0, end=None):
    """First index in words[start:end] where toks appears closely enough.

    Pass 1 is positional. Pass 2 exists because Whisper substitutes homophones
    in Chinese ("蓝色鲸鱼" comes back as "蓝色金鱼"), which kills a positional
    match on one character and leaves the line with no anchor at all -- it then
    gets interpolated into whatever gap is left and lands seconds late. Pass 2
    still anchors on the first character and counts the rest as a bag over a
    short window, so one wrong character no longer discards the anchor.
    """
    if not toks or not words:
        return None
    limit = len(words) if end is None else min(end, len(words))
    probe = toks[:6]
    need = max(1, min(3, len(toks)) - 1)

    best, best_hits = None, 0
    for i in range(start, max(start, limit - len(toks) + 1)):
        hits = 0
        for k, t in enumerate(probe):
            if i + k < len(words) and words[i + k][0] == t:
                hits += 1
        if hits > best_hits:
            best, best_hits = i, hits
        if hits >= max(1, min(len(toks), 3)):
            return i
    if best_hits >= need:
        return best

    if any(CJK.match(t) for t in toks):
        win = max(len(toks), 4)
        bag_need = max(2, int(len(probe) * 0.5))
        bbest, bhits = None, 0
        for i in range(start, max(start, limit - win + 1)):
            if words[i][0] != toks[0]:
                continue
            window = [x[0] for x in words[i:i + win]]
            h = sum(1 for t in probe if t in window)
            if h > bhits:
                bbest, bhits = i, h
        if bhits >= bag_need:
            return bbest
    return None


def similarity(a, b):
    if not a or not b:
        return 0.0
    ratio = SequenceMatcher(None, a, b).ratio()
    if CJK.search(a) or CJK.search(b):
        ratio = max(ratio, SequenceMatcher(None, pinyin_text(a), pinyin_text(b)).ratio())
    ta, tb = set(tokens_of(a)), set(tokens_of(b))
    jac = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    return 0.6 * ratio + 0.4 * jac


def parse_lyrics(path):
    blocks, section, lines = [], "", []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            m = SECTION_RE.match(line)
            if m:
                if lines:
                    blocks.append((section, lines))
                section, lines = m.group(1), []
                continue
            lines.append(line)
    if lines:
        blocks.append((section, lines))
    return blocks


def stamp(seconds):
    seconds = max(0.0, seconds)
    m = int(seconds // 60)
    return "[%02d:%05.2f]" % (m, seconds - m * 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", required=True)
    ap.add_argument("--lyrics", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--artist", default="YuE2")
    ap.add_argument("--translation", default="")
    ap.add_argument("--translation-out", default="")
    ap.add_argument("--min-sim", type=float, default=MIN_SIM)
    ap.add_argument("--report", default="")
    args = ap.parse_args()

    import soundfile as sf
    duration = sf.info(args.audio).duration

    data = json.load(open(args.words, encoding="utf-8"))
    all_words = []
    for w in data["words"]:
        toks = split_tokens(w["word"])
        if not toks:
            continue
        # A multi-character Whisper token (normal for Chinese) is spread across
        # its own span so each character gets a usable timestamp.
        step = (w["end"] - w["start"]) / max(len(toks), 1)
        for k, t in enumerate(toks):
            all_words.append((tok_key(t), w["start"] + k * step))

    phrases = []
    for seg in data["segments"]:
        n = norm_text(seg["text"])
        if n:
            phrases.append({
                "start": seg["start"], "end": seg["end"],
                "text": seg["text"].strip(), "norm": n,
                # Whisper often merges two or three lyric lines into one segment;
                # the word timestamps inside it are what lets those lines be split
                # apart again instead of being interpolated.
                "words": [(w, t) for w, t in all_words
                          if seg["start"] - 0.01 <= t < seg["end"] + 0.01],
            })

    blocks = parse_lyrics(args.lyrics)
    lines = [{"section": s, "text": t} for s, ls in blocks for t in ls]
    for ln in lines:
        ln["norm"] = norm_text(ln["text"])

    N, M = len(lines), len(phrases)

    # Global DP, with a small bias toward EARLIER lyric lines.
    #
    # The lyric set repeats whole lines verbatim (the Outro repeats "Am I the
    # reason..." and "There's so much to be said" straight from the Bridge). A
    # plain maximum-similarity DP is indifferent between the first and the later
    # occurrence, anchors the later one, and then crams every line in between into
    # a couple of seconds. The bias only ever breaks near-ties -- a real
    # similarity gap (0.45 vs 0.95) still wins -- so duplicates are consumed at
    # their first real occurrence, which is the one the singer actually reached.
    BIAS = 0.05
    NEG = float("-inf")
    dp = [[NEG] * (M + 1) for _ in range(N + 1)]
    dp[0][0] = 0.0
    for i in range(1, N + 1):
        dp[i][0] = dp[i - 1][0]
    for j in range(1, M + 1):
        dp[0][j] = dp[0][j - 1]

    def bonus(i):
        return BIAS * (N - i) / float(N)

    for i in range(1, N + 1):
        for j in range(1, M + 1):
            best = dp[i - 1][j] if dp[i - 1][j] > dp[i][j - 1] else dp[i][j - 1]
            s = similarity(lines[i - 1]["norm"], phrases[j - 1]["norm"])
            if s >= args.min_sim:
                cand = dp[i - 1][j - 1] + s + bonus(i - 1)
                if cand > best:
                    best = cand
            dp[i][j] = best

    pairs, i, j = [], N, M
    while i > 0 and j > 0:
        s = similarity(lines[i - 1]["norm"], phrases[j - 1]["norm"])
        if s >= args.min_sim and abs(dp[i][j] - (dp[i - 1][j - 1] + s + bonus(i - 1))) < 1e-9:
            pairs.append((i - 1, j - 1, s))
            i, j = i - 1, j - 1
        elif abs(dp[i][j] - dp[i - 1][j]) < 1e-9:
            i -= 1
        else:
            j -= 1
    pairs.reverse()

    anchors = {li: (phrases[pj]["start"], phrases[pj]["end"], s, phrases[pj]["text"], pj)
               for li, pj, s in pairs}

    # Word-level refinement: inside a phrase, place the neighbouring lines on the
    # word timestamps they actually match instead of leaving them to interpolation.
    # A phrase usually spans one or two lyric lines, so the search stays local and
    # cannot create the cross-song false anchors a global word match would.
    refined = 0
    refined_ids = set()
    for li in sorted(anchors):
        pj = anchors[li][4]
        words = phrases[pj]["words"]
        toks = tokens_of(lines[li]["norm"])
        base = find_tokens(words, toks)
        if base is None:
            continue
        # Re-seat the anchor line on its OWN words. The DP anchors a line to the
        # phrase start, but Whisper merges two or three lyric lines into one
        # phrase -- so the anchor sits on the first line's time and any line the
        # refinement puts in front of it lands on the same second and gets thrown
        # away by the monotonicity guard.
        if words[base][1] > anchors[li][0] + 0.01:
            anchors[li] = (words[base][1], anchors[li][1], anchors[li][2], anchors[li][3], pj)
            refined += 1
        cur = base
        k = li - 1
        while k >= 0 and k not in anchors:
            t2 = tokens_of(lines[k]["norm"])
            p = find_tokens(words, t2, 0, cur)
            if p is None:
                break
            anchors[k] = (words[p][1], anchors[li][1], similarity(lines[k]["norm"], phrases[pj]["norm"]),
                          phrases[pj]["text"], pj)
            refined += 1
            refined_ids.add(k)
            cur = p
            k -= 1
        cur = base + len(toks)
        k = li + 1
        while k < len(lines) and k not in anchors:
            t2 = tokens_of(lines[k]["norm"])
            p = find_tokens(words, t2, cur)
            if p is None:
                break
            anchors[k] = (words[p][1], anchors[li][1], similarity(lines[k]["norm"], phrases[pj]["norm"]),
                          phrases[pj]["text"], pj)
            refined += 1
            refined_ids.add(k)
            cur = p + len(t2)
            k += 1

    # The DP anchors are monotonic by construction, so only a refinement can put
    # two lines on the same word or invert their order. Drop just those and let
    # interpolation cover them again.
    while True:
        order = sorted(anchors)
        bad = None
        for a, b in zip(order, order[1:]):
            if anchors[b][0] <= anchors[a][0]:
                bad = b if b in refined_ids else (a if a in refined_ids else None)
                break
        if bad is None:
            break
        refined_ids.discard(bad)
        del anchors[bad]
        refined -= 1

    if refined:
        print("word-level refinement placed %d extra lines" % refined)

    last_anchor = max(anchors) if anchors else -1
    kept = lines[:last_anchor + 1] if last_anchor >= 0 else []
    dropped = len(lines) - len(kept)

    print("whisper phrases : %d" % M)
    print("lyric lines     : %d   anchored %d   unsung (dropped) %d"
          % (N, len(anchors), dropped))
    if dropped:
        print("  dropped from line %d onward:" % (last_anchor + 1))
        for ln in lines[last_anchor + 1:]:
            print("    %s" % ln["text"][:60])

    times = [None] * len(kept)
    for li in anchors:
        if li < len(kept):
            times[li] = anchors[li][0]

    def syl(i):
        return max(1, len(split_tokens(kept[i]["norm"])))

    for i in range(len(kept)):
        if times[i] is not None:
            continue
        lo = next((k for k in range(i - 1, -1, -1) if times[k] is not None), None)
        hi = next((k for k in range(i + 1, len(kept)) if times[k] is not None), None)
        if lo is None:
            times[i] = max(0.0, (times[hi] if hi is not None else 0.0) - 3.0 * ((hi or 0) - i))
        elif hi is None:
            times[i] = times[lo] + 3.0 * (i - lo)
        else:
            span = times[hi] - times[lo]
            w = sum(syl(k) for k in range(lo + 1, i + 1))
            tot = sum(syl(k) for k in range(lo + 1, hi + 1))
            times[i] = times[lo] + span * w / tot

    header = ["[ti:%s]" % (args.title or os.path.splitext(os.path.basename(args.audio))[0]),
              "[ar:%s]" % args.artist,
              "[length:%02d:%05.2f]" % (duration // 60, duration % 60),
              "[by:Whisper phrase timestamps, monotonic-DP matched to the known lyrics]", ""]

    out, last = list(header), None
    for i, ln in enumerate(kept):
        if ln["section"] != last:
            if last is not None:
                out.append("")
            last = ln["section"]
        out.append("%s%s" % (stamp(times[i]), ln["text"]))
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    print("wrote %s  (%d lines)" % (args.out, len(kept)))

    if args.translation and args.translation_out:
        trans = [t for _s, ls in parse_lyrics(args.translation) for t in ls][:len(kept)]
        if len(trans) == len(kept):
            b, last = list(header), None
            for i, ln in enumerate(kept):
                if ln["section"] != last:
                    if last is not None:
                        b.append("")
                    last = ln["section"]
                b.append("%s%s" % (stamp(times[i]), ln["text"]))
                b.append("%s%s" % (stamp(times[i] + 0.20), trans[i]))
            with open(args.translation_out, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("\n".join(b) + "\n")
            print("wrote %s (bilingual)" % args.translation_out)

    print("\n%-4s %-9s %5s  %-42s | whisper heard" % ("line", "time", "sim", "lyric line"))
    print("-" * 118)
    inv, prev = 0, -1.0
    for i, ln in enumerate(kept):
        if times[i] < prev - 0.01:
            inv += 1
        prev = times[i]
        if i in anchors:
            s, heard = anchors[i][2], anchors[i][3]
            print("%-4d %8.2fs %5.2f  %-42s | %s" % (i, times[i], s, ln["text"][:42], heard[:44]))
        else:
            print("%-4d %8.2fs   ---  %-42s | (interpolated)" % (i, times[i], ln["text"][:42]))
    print("\ninversions: %d" % inv)

    if args.report:
        json.dump({"times": times, "kept": kept,
                   "anchors": {str(k): v[0] for k, v in anchors.items()},
                   "similarity": {str(k): v[2] for k, v in anchors.items()},
                   "dropped": [ln["text"] for ln in lines[last_anchor + 1:]]},
                  open(args.report, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("wrote", args.report)


if __name__ == "__main__":
    sys.exit(main())
