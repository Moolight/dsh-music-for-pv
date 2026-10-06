"""Encode a PNG frame sequence plus a song into the PV deliverable.

Kept separate from the renderer on purpose: this is the last mile (frame rate,
colour tags, audio mux) and it can be proven on synthetic frames before any
scene code exists.

The colour handling follows the upstream film: frames are authored in sRGB and
the delivery is tagged and converted to BT.709 limited range with yuv420p, which
is what a player expects.

    python encode_pv.py frames/ --song song.flac --out film.mp4
    python encode_pv.py --selftest            # render 24 dummy frames and encode
"""
from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

FPS = 24
W, H = 1280, 720

BT709 = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
         "-color_range", "tv"]
# ffmpeg's -color_primaries / -color_trc do not reach the bitstream here
# (ffprobe reports them as unknown); the encoders' own params do, so both are
# passed. x265 spells the range differently from x264.
X264_COLOR = ["-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709:range=tv"]
X265_COLOR = ["-x265-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709:range=limited"]


def encode(frames: Path, song: Path | None, out: Path, fps: int = FPS,
           crf: int = 16, duration: float | None = None, audio_ss: float = 0.0,
           scale_to: tuple[int, int] | None = None, codec: str = "libx264",
           head: Path | None = None, tail: Path | None = None) -> None:
    """PNG sequence -> H.264/AAC mp4, BT.709.

    `audio_ss` seeks into the song, so a window rendered from the middle of the
    film can be reviewed with the audio that belongs to it.

    `head` / `tail` are card sequences concatenated around the film (title card
    and end credits). They add to the running time, so the song is delayed by the
    head length -- the film's own frames stay a pure function of song time.

    `scale_to` produces an upscaled delivery. The film is authored at 1280x720
    and 4K is exactly 3x, so it is a clean integer scale -- but done with Lanczos,
    not nearest: three quarters of this film's screen time is Chinese subtitles,
    and pixel-tripling turns 24 px hanzi into visible block edges.
    """
    pattern = frames / "f_%06d.png"
    files = sorted(frames.glob("f_*.png"))
    if not files:
        raise SystemExit(f"no frames matching {pattern}")
    # Frames carry their global index (f_003687.png is frame 3687 of the song), so
    # the sequence does not start at zero. ffmpeg's image2 demuxer assumes it does
    # unless told otherwise, and "Could find no file ... index in the range 0-4" is
    # what that looks like.
    first = int(files[0].stem.split("_")[1])
    out.parent.mkdir(parents=True, exist_ok=True)

    head_n = len(list(head.glob("f_*.png"))) if head else 0
    cmd = ["ffmpeg", "-v", "error", "-y"]
    inputs = []                       # [(dir, start_number)]
    if head:
        cmd += ["-framerate", str(fps), "-start_number", "0", "-i", str(head / "f_%06d.png")]
        inputs.append("head")
    cmd += ["-framerate", str(fps), "-start_number", str(first), "-i", str(pattern)]
    inputs.append("film")
    if tail:
        cmd += ["-framerate", str(fps), "-start_number", "0", "-i", str(tail / "f_%06d.png")]
        inputs.append("tail")
    if song is not None:
        if audio_ss:
            cmd += ["-ss", f"{audio_ss:.3f}"]
        cmd += ["-i", str(song)]
        song_idx = len(inputs)
    else:
        song_idx = None

    vf = "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"
    if scale_to is not None:
        vf = (f"scale={scale_to[0]}:{scale_to[1]}:flags=lanczos," + vf)

    # Always go through -filter_complex (never -vf at the same time: ffmpeg
    # rejects an output stream fed by both). The scale is appended to whichever
    # chain produces the final video, and the song is delayed by the head length
    # so the film's own frames stay a pure function of song time.
    n_video = len(inputs)
    graph = []
    if n_video > 1:
        src = "".join(f"[{i}:v]" for i in range(n_video))
        graph.append(f"{src}concat=n={n_video}:v=1:a=0,{vf}[vout]")
    else:
        graph.append(f"[0:v]{vf}[vout]")
    amap = None
    if song_idx is not None:
        delay_ms = int(round(head_n / fps * 1000))
        graph.append(f"[{song_idx}:a]adelay={delay_ms}|{delay_ms}[aout]")
        amap = "[aout]"

    cmd += ["-filter_complex", ";".join(graph), "-map", "[vout]"]
    if amap:
        cmd += ["-map", amap]

    cmd += ["-c:v", codec, "-crf", str(crf)]
    cmd += ["-preset", "medium" if codec == "libx265" else "slow"]
    cmd += [*BT709, *(X265_COLOR if codec == "libx265" else X264_COLOR)]
    if codec == "libx265":
        cmd += ["-tag:v", "hvc1"]      # so QuickTime and Safari accept it
    if song_idx is not None:
        cmd += ["-c:a", "aac", "-b:a", "320k"]
    if duration is not None:
        cmd += ["-t", f"{duration:.3f}"]
    cmd += ["-movflags", "+faststart", str(out)]

    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)
    size = out.stat().st_size / 1e6
    print(f"wrote {out}  ({size:.1f} MB)")


def selftest(root: Path) -> None:
    """Render 24 frames of a moving test pattern and encode them, so the ffmpeg
    leg and the colour tags are proven before the scene code exists."""
    frames = root / "out" / "_selftest_frames"
    if frames.exists():
        shutil.rmtree(frames)
    frames.mkdir(parents=True)
    for i in range(24):
        im = Image.new("RGB", (W, H), (4, 7, 15))
        d = ImageDraw.Draw(im)
        x = int(40 + (W - 160) * i / 23)
        d.rectangle([x, 300, x + 80, 420], fill=(77, 107, 254))
        d.rectangle([20, 660, W - 20, 700], outline=(200, 214, 234))
        d.text((32, 672), f"selftest frame {i:02d}  ({i / FPS:.3f}s)", fill=(200, 214, 234))
        for k in range(0, W, 40):
            v = int(120 + 100 * math.sin((k + i * 12) / 90))
            d.line([k, 120, k, 120 + v], fill=(255, 176, 0))
        im.save(frames / f"f_{i:06d}.png")
    print("rendered", len(list(frames.glob('*.png'))), "frames ->", frames)
    encode(frames, None, root / "out" / "_selftest.mp4", duration=1.0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("frames", nargs="?", help="directory of f_NNNNNN.png")
    ap.add_argument("--song", help="audio to mux")
    ap.add_argument("--out", default="out/film.mp4")
    ap.add_argument("--fps", type=int, default=FPS)
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--duration", type=float, default=None, help="trim to this many seconds")
    ap.add_argument("--audio-ss", type=float, default=0.0,
                    help="seek into the song before muxing (for rendering a window)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--4k", dest="k4", action="store_true",
                    help="also write a 3840x2160 HEVC version next to --out")
    ap.add_argument("--head", default="", help="title-card frame sequence")
    ap.add_argument("--tail", default="", help="end-credit frame sequence")
    a = ap.parse_args()

    root = Path(__file__).resolve().parent
    if a.selftest:
        selftest(root)
        return
    if not a.frames:
        ap.error("give a frames directory, or --selftest")
    song = Path(a.song).resolve() if a.song else None
    if song and not song.exists():
        sys.exit(f"no such song: {song}")
    frames = Path(a.frames).resolve()
    out = Path(a.out).resolve()
    head = Path(a.head).resolve() if a.head else None
    tail = Path(a.tail).resolve() if a.tail else None
    encode(frames, song, out, a.fps, a.crf, a.duration, a.audio_ss,
           head=head, tail=tail)
    if a.k4:
        k4 = out.with_name(out.stem + "_4k" + out.suffix)
        encode(frames, song, k4, a.fps, 18, a.duration, a.audio_ss,
               scale_to=(3840, 2160), codec="libx265", head=head, tail=tail)


if __name__ == "__main__":
    main()
