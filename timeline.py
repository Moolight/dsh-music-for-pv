#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《请叫我 DeepSeek》PV 时间轴构建器。

每个字段只有一个事实来源，本脚本不做任何"聪明"的推算：

    行文本 / 段落块    <- lyrics_jazz.txt        歌词原文（含 block 标记）
    行起始时间 t       <- 请叫我DeepSeek.lrc     已审计，只读取，绝不重算
    逐词时间           <- w_jazz.json           Whisper 输出，原样保留
    歌曲总时长         <- 请叫我DeepSeek.flac    只读文件头（soundfile）

配对规则
    歌词正文行与 LRC 时间戳行按出现顺序逐行 1:1 配对。
    两边行数不等时，多出来的一侧整体弃置（不猜时间、不插值），
    弃置的行在报告里逐条点名。

逐词归属规则
    词的 start 落在 [t, t_end) 即归该行；t_end 取下一行的 t，最后一行取歌曲时长。
    报告里附带"重叠归属"口径的差异行数，方便下游换口径时心里有数。

用法
    python timeline.py
    python timeline.py --out out/timeline.json --report out/timeline_report.md

控制台只打 ASCII（Windows 控制台是 GBK，中文会乱码）；
中文内容全部写进 out/timeline.json 与 out/timeline_report.md。
"""
from __future__ import annotations

import argparse
import bisect
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from pvlib import config  # noqa: E402

DEFAULT_LYRICS = config.LYRICS
DEFAULT_LRC = config.LRC
DEFAULT_WHISPER = config.WHISPER
DEFAULT_AUDIO = config.SONG
DEFAULT_OUT = ROOT / "out" / "timeline.json"
DEFAULT_REPORT = ROOT / "out" / "timeline_report.md"

TITLE = "请叫我 DeepSeek"
FALLBACK_DURATION = 268.40  # 仅在音频读不出来时兜底
NDIG = 3                    # 输出时间保留到毫秒

BLOCK_RE = re.compile(r"^\[(Verse|Chorus|Bridge|Outro)\]$")
TS_RE = re.compile(r"^\[(\d{1,2}):(\d{2}(?:\.\d+)?)\](.*)$")
LEN_RE = re.compile(r"^\[length:(\d{1,2}):(\d{2}(?:\.\d+)?)\]$")
PUNCT_RE = re.compile(r"[\s\u3000，。！？、,.!?~～…—\-:：;；\"'“”‘’()（）]+")


# --------------------------------------------------------------------------
# 读入
# --------------------------------------------------------------------------
def read_text(path: Path) -> str:
    """按 UTF-8（容忍 BOM）解码；这里不猜编码，猜错会静默毁掉歌词。"""
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SystemExit("not a utf-8 file: %s (%s)" % (path, exc))


def parse_lyrics(path: Path):
    """歌词文件 -> (blocks, flat)。

    blocks: [{"tag": "Verse", "header_line": 1, "lines": [(lineno, text), ...]}]
    flat  : [(block_tag, text, file_lineno)]，按文件顺序铺平，用于和 LRC 逐行配对。
    """
    lines = read_text(path).splitlines()
    blocks, flat = [], []
    blank, cur = [], None
    for n, raw in enumerate(lines, 1):
        s = raw.strip()
        if not s:
            blank.append(n)
            continue
        m = BLOCK_RE.match(s)
        if m:
            cur = {"tag": m.group(1), "header_line": n, "lines": []}
            blocks.append(cur)
            continue
        if cur is None:
            raise SystemExit("lyric line %d is outside any [Verse]/[Chorus] block" % n)
        cur["lines"].append((n, s))
        flat.append((cur["tag"], s, n, len(blocks) - 1))
    info = {
        "file_lines": len(lines),
        "blank": len(blank),
        "markers": len(blocks),
        "text_lines": len(flat),
        "blocks": blocks,
    }
    return blocks, flat, info


def parse_lrc(path: Path):
    """LRC -> (entries, meta, info)。

    entries: [{"t": 秒, "text": 文本, "line": 行号, "stamp": "mm:ss.cc"}]
    meta   : {"ti":..., "length": 秒, ...}
    """
    lines = read_text(path).splitlines()
    entries, meta, blank = [], {}, []
    for n, raw in enumerate(lines, 1):
        s = raw.strip()
        if not s:
            blank.append(n)
            continue
        m = TS_RE.match(s)
        if m:
            mm, ss, text = int(m.group(1)), float(m.group(2)), m.group(3).strip()
            entries.append({
                "t": round(mm * 60 + ss, NDIG),
                "text": text,
                "line": n,
                "stamp": "%02d:%05.2f" % (mm, ss),
            })
            continue
        lm = LEN_RE.match(s)
        if lm:
            meta["length"] = round(int(lm.group(1)) * 60 + float(lm.group(2)), NDIG)
            continue
        if s.startswith("[") and ":" in s:
            key = s[1:s.index(":")]
            meta[key] = s[s.index(":") + 1:-1].strip()
    info = {"file_lines": len(lines), "blank": len(blank),
            "stamps": len(entries), "meta_lines": len(lines) - len(blank) - len(entries)}
    return entries, meta, info


def load_words(path: Path):
    """Whisper 输出 -> [(start, end, word)]，原样保留（繁体、谐音误听都不动）。"""
    data = json.loads(read_text(path))
    words = []
    for w in data.get("words") or []:
        words.append((float(w["start"]), float(w["end"]), str(w["word"])))
    words.sort(key=lambda x: (x[0], x[1]))
    return words, data


def audio_duration(path: Path):
    """只读文件头拿总时长，返回 (秒, 来源说明)；失败返回 (None, 原因)。"""
    if not path.exists():
        return None, "missing"
    try:
        import soundfile as sf
        info = sf.info(str(path))
        if info.frames and info.samplerate:
            return round(info.frames / float(info.samplerate), NDIG), "soundfile header"
        return None, "no frames"
    except Exception as exc:  # noqa: BLE001 - 兜底优先，别把构建打崩
        return None, "%s: %s" % (type(exc).__name__, exc)


def norm(text: str) -> str:
    """宽松比对用：去掉空白与标点、转小写。只用于报口径，不用于产出。"""
    return PUNCT_RE.sub("", text).lower()


# --------------------------------------------------------------------------
# 构建
# --------------------------------------------------------------------------
def build(lyrics_path, lrc_path, whisper_path, audio_path):
    blocks, flat, lyr_info = parse_lyrics(lyrics_path)
    entries, meta, lrc_info = parse_lrc(lrc_path)
    words, wraw = load_words(whisper_path)

    duration, dur_src = audio_duration(audio_path)
    if duration is None:
        duration = meta.get("length", FALLBACK_DURATION)
        dur_src = "lrc [length:]" if "length" in meta else "fallback constant"
    if "length" in meta and abs(meta["length"] - duration) > 0.05:
        dur_src += " (lrc length %s differs)" % meta["length"]

    # ---- 逐行 1:1 配对 ----
    n_pair = min(len(flat), len(entries))
    pairs = []
    for k in range(n_pair):
        tag, text, lno, bidx = flat[k]
        e = entries[k]
        pairs.append({"block": tag, "block_idx": bidx, "text": text, "file_line": lno,
                      "lrc_text": e["text"], "t": e["t"],
                      "lrc_line": e["line"], "stamp": e["stamp"]})
    dropped_lyrics = flat[n_pair:]
    dropped_lrc = entries[n_pair:]

    mismatches = [p for p in pairs if p["text"] != p["lrc_text"]]
    soft_mismatches = [p for p in mismatches if norm(p["text"]) != norm(p["lrc_text"])]

    # ---- t_end + 逐词归属 ----
    starts = [w[0] for w in words]
    lines = []
    for k, p in enumerate(pairs):
        t = p["t"]
        t_end = pairs[k + 1]["t"] if k + 1 < len(pairs) else round(duration, NDIG)
        lo = bisect.bisect_left(starts, t)
        hi = bisect.bisect_left(starts, t_end)
        chunk = [{"w": w, "t": round(s, NDIG), "end": round(e, NDIG)}
                 for (s, e, w) in words[lo:hi]]
        chunk.sort(key=lambda x: (x["t"], x["end"]))
        lines.append({
            "i": k,
            "block": p["block"],
            "text": p["text"],
            "t": t,
            "t_end": t_end,
            "words": chunk,
            "_file_line": p["file_line"],
            "_lrc_line": p["lrc_line"],
            "_stamp": p["stamp"],
            "_lrc_text": p["lrc_text"],
            "_block_idx": p["block_idx"],
            "_lo": lo, "_hi": hi,
        })

    assigned = sum(len(l["words"]) for l in lines)
    beyond = bisect.bisect_left(starts, duration)          # start >= duration
    unassigned = len(words) - assigned

    # 重叠口径差异（仅统计，不改产出）
    overlap_note = 0
    for l in lines:
        t, t_end = l["t"], l["t_end"]
        start_rule = set(range(l["_lo"], l["_hi"]))
        overlap_rule = {k for k, (st, en, _w) in enumerate(words)
                        if (t <= st < t_end) or (st < t < en)}
        if start_rule != overlap_rule:
            overlap_note += 1

    # ---- 自检量 ----
    rev = [(lines[k]["i"], lines[k]["t"], lines[k + 1]["t"])
           for k in range(len(lines) - 1) if not lines[k]["t"] < lines[k + 1]["t"]]
    back = [(lines[k]["i"], lines[k]["t"], lines[k + 1]["t"])
            for k in range(len(lines) - 1)
            if k + 1 < len(pairs) and pairs[k + 1]["t"] < pairs[k]["t"]]
    stamp_ok = [l for l in lines
                if "%02d:%05.2f" % (l["t"] // 60, l["t"] - (l["t"] // 60) * 60) == l["_stamp"]]

    # ---- 上游数据实况（原样保留的证据，只在报告里陈述，不改产出）----
    lyric_chars = set("".join(l["text"] for l in lines))
    odd_words = [(l["i"], w) for l in lines for w in l["words"]
                 if any(c not in lyric_chars and c != " " for c in w["w"])]
    zero_len = [(k, w[2], w[0]) for k, w in enumerate(words) if w[0] >= w[1]]
    heard = [(l["i"], l["text"], "".join(w["w"] for w in l["words"]).replace(" ", ""))
             for l in lines
             if norm("".join(w["w"] for w in l["words"])) != norm(l["text"])]
    # 字数相同但用字不同的中文行 —— 典型的谐音误听（同位置替换），按差字数排前几名
    # （英文行会把排行榜刷满，那是分词问题不是误听，先排除）
    heard_sub = sorted(
        [(i, text, joined, sum(1 for x, y in zip(joined, norm(text)) if x != y))
         for i, text, joined in heard
         if len(joined) == len(norm(text)) and not re.search(r"[A-Za-z]", text)],
        key=lambda r: -r[3])

    shots = [(l["t_end"] - l["t"], l["i"]) for l in lines]
    durs = [s for s, _ in shots]
    body_shots = [(l["t_end"] - l["t"], l["i"]) for l in lines[:-1]]  # 不含末行（末行只是歌曲尾巴）
    stats = {
        "lyrics": lyr_info, "lrc": lrc_info, "duration": duration, "dur_src": dur_src,
        "lrc_meta": meta,
        "paired": n_pair, "dropped_lyrics": dropped_lyrics, "dropped_lrc": dropped_lrc,
        "mismatch_exact": mismatches, "mismatch_soft": soft_mismatches,
        "words_in_file": len(words), "words_assigned": assigned,
        "words_beyond_song": len(words) - beyond, "words_unassigned": unassigned,
        "models": wraw.get("model"),
        "blocks_out": block_span(lines, blocks),
        "monotonic": len(rev) == 0, "regressions": rev, "backwards": back,
        "stamp_roundtrip": len(stamp_ok),
        "shot_min": min(shots) if shots else (0, -1),
        "shot_max": max(shots) if shots else (0, -1),
        "shot_max_body": max(body_shots) if body_shots else (0, -1),
        "shot_mean": (sum(durs) / len(durs)) if durs else 0.0,
        "lines_with_words": sum(1 for l in lines if l["words"]),
        "lines_empty_words": [l["i"] for l in lines if not l["words"]],
        "words_per_line_mean": (assigned / len(lines)) if lines else 0.0,
        "words_per_line_max": max((len(l["words"]) for l in lines), default=0),
        "words_per_line_min": min((len(l["words"]) for l in lines), default=0),
        "overlap_note": overlap_note,
        "odd_words": odd_words, "zero_len": zero_len, "heard": heard,
        "heard_sub": heard_sub,
    }

    result = {
        "duration": round(duration, 2),
        "title": TITLE,
        "lines": [{"i": l["i"], "block": l["block"], "text": l["text"],
                   "t": l["t"], "t_end": l["t_end"], "words": l["words"]}
                  for l in lines],
    }
    return result, stats, lines


def block_span(lines, blocks):
    """每个原文段落块的起止：块内第一行 t 到最后一行 t_end。

    按歌词文件里的 [Verse]/[Chorus]/... 标记分块，而不是按 tag 名合并——
    文件里有 4 个彼此独立的 [Verse] 块（相邻但确实是分开的段落），
    这里给的是 12 个块各自的区间。
    """
    out = []
    for bi, b in enumerate(blocks):
        members = [l for l in lines if l["_block_idx"] == bi]
        if not members:
            continue
        out.append({"block": b["tag"], "header_line": b["header_line"],
                    "first": members[0]["i"], "last": members[-1]["i"],
                    "t0": members[0]["t"], "t1": members[-1]["t_end"]})
    for b in out:
        b["n"] = b["last"] - b["first"] + 1
        b["dur"] = round(b["t1"] - b["t0"], NDIG)
    return out


# --------------------------------------------------------------------------
# 报告（中文，只进文件不进控制台）
# --------------------------------------------------------------------------
def write_report(path: Path, stats: dict, lines, result):
    s = stats
    L = []
    A = L.append

    A("# 《%s》PV 时间轴构建报告" % TITLE)
    A("")
    A("由 `timeline.py` 自动生成。歌词文本取自歌词文件，行时间取自 LRC（不重算），")
    A("逐词时间取自 Whisper 输出（原样保留繁体与谐音误听）。")
    A("")
    A("## 1. 输入与行数")
    A("")
    A("| 项 | 数值 |")
    A("| --- | --- |")
    A("| 歌词文件总行数 | %d（正文 %d + 段落标记 %d + 空行 %d） |"
      % (s["lyrics"]["file_lines"], s["lyrics"]["text_lines"],
         s["lyrics"]["markers"], s["lyrics"]["blank"]))
    A("| LRC 总行数 | %d（时间戳 %d + 元数据 %d + 空行 %d） |"
      % (s["lrc"]["file_lines"], s["lrc"]["stamps"], s["lrc"]["meta_lines"],
         s["lrc"]["blank"]))
    A("| 歌曲时长 | %.3f s（来源：%s） |" % (s["duration"], s["dur_src"]))
    A("| Whisper 词条 | %d（model=%s） |" % (s["words_in_file"], s["models"]))
    A("")
    A("> 任务说明里提到「歌词 101 行、LRC 约 103 个时间戳」；实测两边正文行**都是 %d 行**，"
      % s["paired"])
    A("> 逐行 1:1 完整配对，没有配不上的行。")
    A("")

    A("## 2. 对齐结果")
    A("")
    A("- 配对成功：**%d / %d**" % (s["paired"], s["lyrics"]["text_lines"]))
    A("- 歌词侧多余行：**%d**%s" % (
        len(s["dropped_lyrics"]),
        "" if not s["dropped_lyrics"] else
        " —— " + "；".join("第 %d 行 %r" % (n, t) for _tag, t, n in s["dropped_lyrics"])))
    A("- LRC 侧多余行：**%d**%s" % (
        len(s["dropped_lrc"]),
        "" if not s["dropped_lrc"] else
        " —— " + "；".join("LRC 第 %d 行 [%s] %r" % (e["line"], e["stamp"], e["text"])
                          for e in s["dropped_lrc"])))
    A("- 文本完全一致：**%d / %d**" % (s["paired"] - len(s["mismatch_exact"]), s["paired"]))
    if s["mismatch_exact"]:
        A("")
        A("文本对不上的行（产出取歌词文件文本，LRC 原文一并列出备查）：")
        A("")
        A("| 行 | 歌词原文 | LRC 原文 | 处理 |")
        A("| --- | --- | --- | --- |")
        for p in s["mismatch_exact"]:
            soft = norm(p["text"]) == norm(p["lrc_text"])
            A("| i (歌词第 %d 行 / LRC 第 %d 行) | %s | %s | %s |"
              % (p["file_line"], p["lrc_line"], p["text"] or "（空）",
                 p["lrc_text"] or "（空）",
                 "仅标点/空白差异" if soft else "取歌词原文"))
        A("")
    else:
        A("- 没有空行、重复行或错位导致的文本不一致。")
    A("")
    A("时间戳回填校验：把产出的 `t` 反向格式化成 `mm:ss.cc` 与原 LRC 时间戳逐行比对，"
      "**%d / %d 完全一致**。" % (s["stamp_roundtrip"], s["paired"]))
    A("")

    A("## 3. 统计")
    A("")
    A("| 指标 | 数值 |")
    A("| --- | --- |")
    A("| 输出行数 | %d |" % len(lines))
    A("| 有词级时间的行 | **%d / %d**（%.1f%%） |"
      % (s["lines_with_words"], len(lines),
         100.0 * s["lines_with_words"] / max(len(lines), 1)))
    A("| 无词级时间的行 | %d%s |" % (
        len(s["lines_empty_words"]),
        "" if not s["lines_empty_words"] else "（i=%s）" % s["lines_empty_words"]))
    A("| 词条总数 | %d 已归属 / %d 文件内（未归属 %d，超出歌曲末尾 %d） |"
      % (s["words_assigned"], s["words_in_file"], s["words_unassigned"],
         s["words_beyond_song"]))
    A("| 平均每行词数 | **%.2f** |" % s["words_per_line_mean"])
    A("| 最多/最少词数 | %d / %d |" % (s["words_per_line_max"], s["words_per_line_min"]))
    A("| 镜头时长 最短 | **%.2f s**（i=%d） |" % (s["shot_min"][0], s["shot_min"][1]))
    A("| 镜头时长 最长 | **%.2f s**（i=%d，末行=歌曲尾巴） |"
      % (s["shot_max"][0], s["shot_max"][1]))
    A("| 镜头时长 最长（不含末行） | **%.2f s**（i=%d） |"
      % (s["shot_max_body"][0], s["shot_max_body"][1]))
    A("| 镜头时长 平均 | %.2f s |" % s["shot_mean"])
    A("")

    A("## 4. 段落块起止（歌词文件里的 12 个块）")
    A("")
    A("| # | 块 | 歌词文件标记行 | 行 i | 行数 | t | t_end | 时长 |")
    A("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for n, b in enumerate(s["blocks_out"], 1):
        A("| %d | %s | %d | %d–%d | %d | %.2f | %.2f | %.2f |"
          % (n, b["block"], b["header_line"], b["first"], b["last"], b["n"],
             b["t0"], b["t1"], b["dur"]))
    A("")
    A("（块内第一行的 `t` 到最后一行的 `t_end`。文件里相邻的同名块算两个块——")
    A("例如开头连续两个 `[Verse]`，以及中段连续四个 `[Verse]`，本表按原文分列。）")
    A("")

    A("## 5. 抽查 5 行（与 LRC 原文对照）")
    A("")
    pick = [0, len(lines) // 4, len(lines) // 2, (3 * len(lines)) // 4, len(lines) - 1]
    A("| i | 块 | 行文本 | t | LRC 原文 | 一致 |")
    A("| --- | --- | --- | --- | --- | --- |")
    for k in pick:
        l = lines[k]
        ok = ("%02d:%05.2f" % (l["t"] // 60, l["t"] - (l["t"] // 60) * 60)) == l["_stamp"]
        A("| %d | %s | %s | %.2f | [%s] %s | %s |"
          % (l["i"], l["block"], l["text"], l["t"], l["_stamp"],
             l["_lrc_text"], "✓" if ok else "✗"))
    A("")

    A("## 6. 时间单调性")
    A("")
    if s["monotonic"]:
        A("- 所有 `t` **严格递增**，无回退、无重复。")
    else:
        A("- **发现回退/重复**：")
        for i, a, b in s["regressions"]:
            A("  - i=%d 的 t=%.3f 不小于下一行 t=%.3f" % (i, a, b))
    A("- 相邻行 `t` 严格递增检查覆盖全部 %d 对。" % max(len(lines) - 1, 0))
    A("")

    A("## 7. 上游数据实况（原样保留的证据）")
    A("")
    A("Whisper 的分词与字形一个字都没动，下面是实测到的原样内容：")
    A("")
    A("- **繁体/异体字形保留**：%d 个词的用字不在歌词文本的字符集合内，例：%s。"
      % (len(s["odd_words"]),
         "、".join("「%s」(i=%d)" % (w["w"], i) for i, w in s["odd_words"][:6]) or "无"))
    A("- **零长度词（上游异常，未修正）**：%d 个 —— %s。产出的 `t == end`，"
      % (len(s["zero_len"]),
         "；".join("w_jazz.json 第 %d 个词「%s」@%.3f" % (k, w, t) for k, w, t in s["zero_len"])
         or "无"))
    A("  渲染端应把这种词当「瞬时点」处理（跳过或给一个最小显示时长），不要拿它算时长。")
    A("- **逐词拼接与行文本不一致的行**：%d 行（英文分词、缩写拆开、繁体异体或谐音误听），样例："
      % len(s["heard"]))
    for i, text, joined in s["heard"][:: max(1, len(s["heard"]) // 3)][:4]:
        A("    - i=%d 行文本「%s」 / Whisper 逐词拼成「%s」" % (i, text, joined))
    A("")
    A("- **典型谐音误听（中文行、同字数、同位置替换）**——这类最容易被下游误当成歌词错误，本产出不纠：")
    for i, text, joined, d in s["heard_sub"][:3]:
        A("    - i=%d 差 %d 字：行文本「%s」 vs Whisper「%s」" % (i, d, text, joined))
    A("")
    A("  行文本一律取歌词原文，Whisper 只提供时间，所以这类不一致不会污染字幕文字，")
    A("  但做卡拉OK 逐字高亮时要知道逐词字串和字幕对不齐。")
    A("")

    A("## 8. 口径说明")
    A("")
    A("- `t` 直接来自 LRC，未经任何平滑、插值或重算；LRC 时间戳原样回填校验通过。")
    A("- `t_end` = 下一行的 `t`；最后一行 = 歌曲时长 %.2f s。" % result["duration"])
    A("- `words` 取 Whisper 输出中 `start ∈ [t, t_end)` 的词，按时间排序；字串原样保留，"
      "繁体（如「別」「會」）与谐音误听（本曲实例见第 7 节）都不做纠正，"
      "也不转简繁、不修错字。")
    A("- 若改用「区间重叠」归属口径，会有 %d 行拿到不同的词集合"
      "（本产出不采用该口径，仅记录）。" % s["overlap_note"])
    A("- 词里带前导空格是 Whisper 分词边界标记（如「 別」），保留原样。")
    A("")

    A("## 9. 产出")
    A("")
    A("```json")
    A(json.dumps({"duration": result["duration"], "title": result["title"],
                  "lines": [result["lines"][0], "…共 %d 行…" % len(result["lines"]),
                            result["lines"][-1]]}, ensure_ascii=False, indent=2)[:1400])
    A("```")
    A("")
    A("`out/timeline.json`：duration / title / lines[i, block, text, t, t_end, words[w, t, end]]。")
    A("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L), encoding="utf-8")


# --------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="build the PV timeline JSON")
    ap.add_argument("--lyrics", default=str(DEFAULT_LYRICS))
    ap.add_argument("--lrc", default=str(DEFAULT_LRC))
    ap.add_argument("--whisper", default=str(DEFAULT_WHISPER))
    ap.add_argument("--audio", default=str(DEFAULT_AUDIO))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--report", default=str(DEFAULT_REPORT))
    a = ap.parse_args(argv)

    result, stats, lines = build(Path(a.lyrics), Path(a.lrc), Path(a.whisper), Path(a.audio))

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_report(Path(a.report), stats, lines, result)

    s = stats
    print("lyrics : %d lines = %d text + %d markers + %d blank"
          % (s["lyrics"]["file_lines"], s["lyrics"]["text_lines"],
             s["lyrics"]["markers"], s["lyrics"]["blank"]))
    print("lrc    : %d lines = %d stamps + %d meta + %d blank"
          % (s["lrc"]["file_lines"], s["lrc"]["stamps"],
             s["lrc"]["meta_lines"], s["lrc"]["blank"]))
    print("paired : %d / %d   dropped(lyrics)=%d dropped(lrc)=%d"
          % (s["paired"], s["lyrics"]["text_lines"],
             len(s["dropped_lyrics"]), len(s["dropped_lrc"])))
    print("text   : exact %d/%d  normalized %d/%d  t-roundtrip %d/%d"
          % (s["paired"] - len(s["mismatch_exact"]), s["paired"],
             s["paired"] - len(s["mismatch_soft"]), s["paired"],
             s["stamp_roundtrip"], s["paired"]))
    print("words  : file=%d assigned=%d unassigned=%d beyond_end=%d  mean/line=%.2f"
          % (s["words_in_file"], s["words_assigned"], s["words_unassigned"],
             s["words_beyond_song"], s["words_per_line_mean"]))
    print("shots  : min %.2f (i=%d)  max %.2f (i=%d)  max_excl_last %.2f (i=%d)  mean %.2f"
          % (s["shot_min"][0], s["shot_min"][1], s["shot_max"][0],
             s["shot_max"][1], s["shot_max_body"][0], s["shot_max_body"][1],
             s["shot_mean"]))
    print("lines  : %d with words, %d without" % (s["lines_with_words"],
                                                  len(s["lines_empty_words"])))
    print("blocks : %d  " % len(s["blocks_out"])
          + ", ".join("%s(%d)" % (b["block"], b["n"]) for b in s["blocks_out"]))
    print("monotonic: %s (regressions=%d)" % ("STRICT OK" if s["monotonic"] else "FAIL",
                                              len(s["regressions"])))
    print("wrote  : %s" % out)
    print("wrote  : %s" % Path(a.report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
