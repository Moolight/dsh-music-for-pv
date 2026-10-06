"""Audit an LRC against what the song actually sings, sentence by sentence.

Two separate questions, deliberately answered separately:

1. IS THE TIMING RIGHT?  Sweep a global offset over the lyrics and report which
   offset maximises the total line-to-audio similarity. If the best offset is
   near zero, the LRC's timing is sound and any remaining mismatch is the
   singer's articulation, not the subtitle.
2. IS EACH SENTENCE IN THE RIGHT PLACE?  For every line, also search the WHOLE
   transcript for the best matching window. If a line's assigned time is far
   from where its words actually appear, that line is misplaced -- a different
   defect from a garbled line, and the one worth fixing.

usage: audit_lrc.py --words w.json --lyrics l.txt --lrc out.lrc --text-out r.txt
"""
import argparse
import io
import json
import re
import sys
from contextlib import redirect_stdout
from difflib import SequenceMatcher
from pathlib import Path

# the matcher lives next to this file
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_lrc_from_whisper import norm_text, parse_lyrics, similarity, split_tokens  # noqa: E402


def load_words(path):
    data = json.load(open(path, encoding="utf-8"))
    toks = []
    for w in data["words"]:
        parts = split_tokens(w["word"])
        if not parts:
            continue
        step = (w["end"] - w["start"]) / max(len(parts), 1)
        for k, p in enumerate(parts):
            toks.append((p, w["start"] + k * step))
    segs = [(s["start"], s["end"], s["text"].strip()) for s in data["segments"]]
    return toks, segs


def heard_between(segs, a, b):
    return " ".join(t for s, e, t in segs if e > a and s < b)


def text_similarity(a, b):
    return similarity(norm_text(a), norm_text(b))


def best_window(tokens, line, span):
    tgt = "".join(split_tokens(norm_text(line)))
    if not tgt or not tokens:
        return None, 0.0
    best_i, best_s = None, 0.0
    for i in range(0, max(1, len(tokens) - span + 1)):
        win = "".join(t for t, _ in tokens[i:i + span])
        s = SequenceMatcher(None, win, tgt).ratio()
        if s > best_s:
            best_i, best_s = i, s
    return (tokens[best_i][1] if best_i is not None else None), best_s


def run(args):
    tokens, segs = load_words(args.words)
    blocks = parse_lyrics(args.lyrics)
    lines = [t for _s, ls in blocks for t in ls]

    lrc = open(args.lrc, encoding="utf-8").read()
    entries = [(int(m.group(1)) * 60 + float(m.group(2)), m.group(3))
               for m in re.finditer(r"^\[(\d+):([\d.]+)\](.*)$", lrc, re.M)
               if m.group(3).strip()]

    def sim_at(off):
        vals = []
        for k, (t, txt) in enumerate(entries):
            end = entries[k + 1][0] if k + 1 < len(entries) else t + 4
            heard = heard_between(segs, t + off, end + off)
            if heard:
                vals.append(text_similarity(txt, heard))
        return sum(vals) / len(vals) if vals else 0.0

    print("=" * 100)
    print("1) 时间是否整体对齐 —— 全局偏移扫描")
    print("=" * 100)
    best_off, best_val = 0.0, -1
    for step in range(-30, 31):
        v = sim_at(step * 0.1)
        if v > best_val:
            best_off, best_val = step * 0.1, v
    print("%8s %10s" % ("offset", "mean sim"))
    for off in (best_off - 0.5, best_off, best_off + 0.5):
        print("%+7.1fs %10.3f" % (off, sim_at(off)))
    print("\n  最佳偏移 %+.1fs  ->  %s" % (
        best_off,
        "LRC 时间轴准确，剩余不一致来自咬字" if abs(best_off) < 0.6
        else "整体偏了 %.1f 秒，需要校正" % best_off))

    print()
    print("=" * 100)
    print("2) 逐句是否落在正确位置（本地相似 = 该时间点听到的与歌词的相似度）")
    print("=" * 100)
    print("%-5s %-9s %-7s %-13s %-7s %s" % ("#", "lrc 时间", "本地", "全曲最佳", "偏移", "歌词 | 实际听到"))
    print("-" * 100)
    misfiled, weak, ok = [], [], 0
    for i, (t, txt) in enumerate(entries):
        end = entries[i + 1][0] if i + 1 < len(entries) else t + 4
        heard = heard_between(segs, t, end)
        local = text_similarity(txt, heard)
        span = max(1, int(round((end - t) * 3.9)))
        bt, bs = best_window(tokens, txt, span)
        delta = (bt - t) if bt is not None else None
        if local < 0.35 and bs > local + 0.25 and delta is not None and abs(delta) > 4:
            misfiled.append((i, t, bt, txt))
        elif local < 0.3:
            weak.append((i, t, txt))
        else:
            ok += 1
        print("%-5d %-9.2f %-7.2f %-13s %-7s %s" % (
            i, t, local,
            ("%.2f/%.2f" % (bt, bs)) if bt is not None else "-",
            ("%+.1f" % delta) if delta is not None else "-",
            txt + "  |  " + heard[:46]))

    print()
    print("=" * 100)
    print("汇总：句子位置正确 %d / %d (%.0f%%)   明显错位 %d   弱匹配 %d"
          % (ok, len(entries), 100.0 * ok / max(len(entries), 1), len(misfiled), len(weak)))
    if misfiled:
        print("\n候选错位（副歌重复句会被误判，需看本地相似度一起判断）：")
        for i, t, bt, txt in misfiled:
            print("  #%d  标在 %.1fs，全曲最像的位置在 %.1fs   %s" % (i, t, bt, txt))
    if weak:
        print("\n弱匹配行号：%s" % ", ".join("#%d" % i for i, _t, _x in weak))
    return {"best_offset": best_off, "misfiled": misfiled, "weak": weak}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", required=True)
    ap.add_argument("--lyrics", required=True)
    ap.add_argument("--lrc", required=True)
    ap.add_argument("--report", default="")
    ap.add_argument("--text-out", default="",
                    help="UTF-8 copy of the report; PowerShell redirection mangles CJK")
    args = ap.parse_args()

    if args.text_out:
        buf = io.StringIO()
        with redirect_stdout(buf):
            result = run(args)
        text = buf.getvalue()
        open(args.text_out, "w", encoding="utf-8").write(text)
        sys.stdout.write(text.encode("ascii", "replace").decode("ascii"))
        print("wrote", args.text_out)
    else:
        result = run(args)

    if args.report:
        json.dump(result, open(args.report, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    sys.exit(main())
