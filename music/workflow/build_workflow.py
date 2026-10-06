"""Build a ComfyUI workflow (API format) for a YuE2 song.

Nodes and widget order are derived from /object_info rather than hardcoded, so a
ComfyUI upgrade that adds an input does not silently produce a malformed graph.

    python build_workflow.py [seed] [suffix] [max_duration] [ref] [full|melody]

    SONG_STYLE     style prompt file        (default ../style.txt)
    SONG_LYRICS    lyric sheet file         (default ../../input/lyrics.txt)
    SONG_REF       reference audio          (only read when "ref" is passed)
    SONG_TITLE     song title -- ASCII ONLY (default CallMeDeepSeek)
    SONG_STEM      output stem override
    SONG_ABCGEN=1  let YuE2GenerateABC write the score first
    SONG_REP_PEN   repetition penalty       (default 1.35)

Runs free by default -- no reference audio, YuE2 writes its own melody around the
lyrics. That is the route the released song used; `ref` restores the cover route.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

API = os.environ.get("COMFY_API", "http://127.0.0.1:8188")
HERE = Path(__file__).resolve().parent
SONG_DIR = HERE.parent                     # music/
PROJECT = SONG_DIR.parent                  # the checkout root

CKPT = "yue2_3b_int8_convrot.safetensors"
ENC = "sheetsage2_bf16.safetensors"

# seed, output suffix and max_duration are overridable so a seed sweep can reuse
# this one builder instead of hand-editing JSON.
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 424242
SUFFIX = sys.argv[2] if len(sys.argv) > 2 else ""
MAX_DUR = float(sys.argv[3]) if len(sys.argv) > 3 else 300.0
# Free is the DEFAULT, because that is what the released song used. Dropping the
# reference ABC lets YuE2 write its own melody around the lyrics; feeding it a
# score transcribed from another song forces the new words onto that song's note
# pattern, which stretches and swallows them (see music/README.md). Pass `ref` as
# the fourth argument to restore the cover route.
FREE = not (len(sys.argv) > 4 and sys.argv[4] == "ref")
# ComfyUI's own tooltip: "full: generates melody and chords; melody: generates
# melody only, recommended for covers."
MODE = sys.argv[5] if len(sys.argv) > 5 else "full"
# SONG_ABCGEN=1 runs ComfyUI's documented non-cover pipeline: YuE2GenerateABC
# writes a score around the lyrics, then YuE2GenerateMusic sings it. Unlike a
# reference-song ABC, that score is not bound to someone else's lyric syllables.
ABCGEN = os.environ.get("SONG_ABCGEN") == "1"
# YuE2 can fall into a repetition loop on longer lyric sheets; the penalty is the
# knob that suppresses it. 1.2 looped from 61 s on this song, 1.35 did not.
REP_PEN = float(os.environ.get("SONG_REP_PEN", "1.35"))
# ASCII only: a Chinese title through a shell pipe comes out mangled and the
# written filename goes with it.
TITLE = os.environ.get("SONG_TITLE", "CallMeDeepSeek")

REF_AUDIO = os.environ.get("SONG_REF", "")
STYLE_PATH = os.environ.get("SONG_STYLE", str(SONG_DIR / "style.txt"))
LYRICS_PATH = os.environ.get("SONG_LYRICS", str(PROJECT / "input" / "lyrics.txt"))
STYLE = open(STYLE_PATH, encoding="utf-8").read().strip()
LYRICS = open(LYRICS_PATH, encoding="utf-8").read().strip()
print("lyrics      :", os.path.basename(LYRICS_PATH), "(%d chars)" % len(LYRICS))
print("style       :", os.path.basename(STYLE_PATH))
print("reference   :", REF_AUDIO or "(none -- free generation)")
print("free/mode   :", FREE, "/", MODE, "  seed", SEED, "  rep_pen", REP_PEN)


# class_type -> {input name: value}. A value of ("@", node, slot) is a link.
SPEC = {
    1:  ("CheckpointLoaderSimple", {"ckpt_name": CKPT}),
    2:  ("AudioEncoderLoader",     {"audio_encoder_name": ENC}),
    3:  ("LoadAudio",              {"audio": REF_AUDIO}),
    4:  ("YuE2GenerateABC", {
            "clip": ("@", 1, 1), "style": STYLE, "lyrics": LYRICS, "seed": SEED,
            "mode": "full", "max_abc_tokens": 8192, "temperature": 0.7, "top_p": 0.9,
            "top_k": 30, "repetition_penalty": 1.005, "penalty_window": 100}
         ) if ABCGEN else (
         "SheetSage2AudioToABC",
         {"audio_encoder": ("@", 2, 0), "audio": ("@", 3, 0), "mode": "full"}),
    5:  ("YuE2GenerateMusic", {
            "clip": ("@", 1, 1), "style": STYLE, "lyrics": LYRICS,
            "abc": ("" if (FREE and not ABCGEN) else ("@", 4, 0)),
            "seed": SEED, "mode": MODE, "max_duration": MAX_DUR, "temperature": 1.0,
            "top_p": 0.95, "top_k": 100, "repetition_penalty": REP_PEN, "cfg_scale": 1.0}),
    6:  ("ConditioningZeroOut",    {"conditioning": ("@", 5, 0)}),
    7:  ("EmptyYuE2LatentAudio",   {"seconds": ("@", 5, 1), "batch_size": 1}),
    8:  ("KSampler", {
            "model": ("@", 1, 0), "positive": ("@", 5, 0), "negative": ("@", 6, 0),
            "latent_image": ("@", 7, 0), "seed": SEED, "steps": 32, "cfg": 1.0,
            "sampler_name": "dpm_2", "scheduler": "sgm_uniform", "denoise": 1.0}),
    9:  ("VAEDecodeAudio",         {"samples": ("@", 8, 0), "vae": ("@", 1, 2)}),
    10: ("SongFilename",           {"title": TITLE, "folder": "audio"}),
    11: ("SaveAudioAdvanced",      {"audio": ("@", 9, 0), "filename_prefix": ("@", 10, 0), "format": "flac"}),
    12: ("SongLyricsToLRC", {
            "lyrics": LYRICS, "seconds": ("@", 5, 1), "audio": ("@", 11, 0),
            "structure": ("@", 4, 0), "title": ("@", 10, 1), "artist": "YuE2",
            "language": "zh", "offset_seconds": 0.0, "timing_scale": 1.0,
            "prefer_alignment": True, "word_timing": True}),
    13: ("SongSaveMatchingLRC",    {"audio": ("@", 11, 0), "lrc": ("@", 12, 0),
                                    "filename_prefix": ("@", 10, 0)}),
}

LINK_TYPES = {"MODEL", "CLIP", "VAE", "CONDITIONING", "LATENT", "AUDIO", "AUDIO_ENCODER",
              "IMAGE", "MASK", "CONTROL_NET", "SAMPLER", "SIGMAS", "GUIDER", "NOISE", "*"}


def load_object_info():
    with urllib.request.urlopen(API + "/object_info", timeout=60) as r:
        return json.load(r)


def declared_inputs(info):
    """[(name, type, opts, is_widget)] in ComfyUI widget/socket declaration order."""
    out = []
    for group in ("required", "optional"):
        for name, spec in (info.get("input") or {}).get(group, {}).items():
            if name.startswith("hidden") or isinstance(spec[0], str) and spec[0] in ("PROMPT", "EXTRA_PNGINFO", "UNIQUE_ID"):
                continue
            opts = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
            if opts.get("hidden"):
                continue
            t = spec[0]
            # V3 nodes report combos as the literal string "COMBO" instead of a list.
            is_widget = (isinstance(t, list)
                         or t in ("INT", "FLOAT", "STRING", "BOOLEAN")
                         or "COMBO" in str(t).upper()) \
                and not opts.get("forceInput")
            out.append((name, t, opts, is_widget))
    return out


def layering(spec):
    """Longest-path column per node id."""
    order, seen = [], set()

    def visit(n):
        if n in seen:
            return
        seen.add(n)
        for v in spec[n][1].values():
            if isinstance(v, tuple) and v[0] == "@":
                visit(v[1])
        order.append(n)

    for n in spec:
        visit(n)
    col = {}
    for n in order:
        deps = [v[1] for v in spec[n][1].values() if isinstance(v, tuple) and v[0] == "@"]
        col[n] = max([col[d] + 1 for d in deps], default=0)
    return col


def main():
    oi = load_object_info()
    col = layering(SPEC)
    row_used = {}
    nodes, links = [], []
    link_id = 100
    exec_order = 0

    for nid in sorted(SPEC, key=lambda n: (col[n], n)):
        ctype, vals = SPEC[nid]
        info = oi[ctype]
        decl = declared_inputs(info)

        inputs, outputs, widgets = [], [], []
        for slot, (name, t, opts, is_widget) in enumerate(decl):
            val = vals.get(name)
            entry = {"name": name, "type": t if isinstance(t, str) else "COMBO"}
            if is_widget:
                entry["widget"] = {"name": name}
                if isinstance(val, tuple) and val[0] == "@":
                    link_id += 1
                    entry["link"] = link_id
                    links.append([link_id, val[1], val[2], nid, len(inputs), entry["type"]])
                    # a converted widget keeps its last literal value as a placeholder
                    widgets.append(opts.get("default", ""))
                else:
                    entry["link"] = None
                    widgets.append(val if val is not None else opts.get("default", ""))
                # seed-style INT widgets carry a trailing control_after_generate combo
                if name in ("seed", "noise_seed"):
                    widgets.append("fixed")
            else:
                if isinstance(val, tuple) and val[0] == "@":
                    link_id += 1
                    entry["link"] = link_id
                    links.append([link_id, val[1], val[2], nid, len(inputs), entry["type"]])
                else:
                    entry["link"] = None
            inputs.append(entry)

        for oname, otype in zip(info.get("output_name") or info["output"], info["output"]):
            outputs.append({"name": oname, "type": otype, "links": []})

        c, r = col[nid], row_used.get(col[nid], 0)
        row_used[col[nid]] = r + 1
        nodes.append({
            "id": nid, "type": ctype, "pos": [c * 420, r * 300], "size": [400, 220],
            "flags": {}, "order": exec_order, "mode": 0,
            "inputs": inputs, "outputs": outputs,
            "properties": {"Node name for S&R": ctype},
            "widgets_values": widgets,
        })
        exec_order += 1

    # back-fill output link ids
    by_id = {n["id"]: n for n in nodes}
    for lid, o_id, o_slot, t_id, t_slot, ltype in links:
        out = by_id[o_id]["outputs"][o_slot]
        out["links"] = (out["links"] or []) + [lid]

    wf = {"id": "c0ffee00-0000-4000-8000-kmn000000001", "revision": 0,
          "last_node_id": max(SPEC), "last_link_id": link_id,
          "nodes": nodes, "links": links, "groups": [],
          "config": {}, "extra": {}, "version": 0.4}

    stem = os.environ.get("SONG_STEM", "know_my_name_yue2" if FREE else "know_my_name_cover")
    out_path = os.path.join(ROOT, "workflow", "%s%s_ui.json" % (stem, SUFFIX))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(wf, f, ensure_ascii=False, indent=1)
    print("wrote", out_path, os.path.getsize(out_path), "bytes")

    # API-format twin, same source of truth
    api_out = {}
    for nid, (ctype, vals) in SPEC.items():
        ins = {}
        for k, v in vals.items():
            ins[k] = [str(v[1]), v[2]] if isinstance(v, tuple) and v[0] == "@" else v
        api_out[str(nid)] = {"class_type": ctype, "inputs": ins}
    api_path = os.path.join(ROOT, "workflow", "%s%s_api.json" % (stem, SUFFIX))
    with open(api_path, "w", encoding="utf-8") as f:
        json.dump(api_out, f, ensure_ascii=False, indent=1)
    print("wrote", api_path, os.path.getsize(api_path), "bytes")
    print("nodes", len(nodes), "links", len(links))
    for n in nodes:
        print("  %2d %-22s widgets=%s" % (n["id"], n["type"], json.dumps(n["widgets_values"], ensure_ascii=False)[:90]))


if __name__ == "__main__":
    main()
