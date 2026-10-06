"""This film's content: the cues that ride on top of the shots.

The engine knows nothing about any of this. `render.py` hands these tables to
`pvlib.band.LyricBand` and `pvlib.overlays.StickerTrack`, so changing what this
film shows is editing this file, not the renderer.

    DECODE_LINES    lines shown as a whole-sentence decode instead of a
                    character-by-character follow-along
    NO_LYRIC        shots that carry no subtitle at all
    NO_LYRIC_HEAD   ... and shots that are wordless only for their first seconds
    STICKERS        the sticker track: (t_in, t_out, tag, name, x, y, width)
"""
from __future__ import annotations

# SHOTS.md 4.2 names four lines as whole-sentence decodes out of noise so the
# viewer reads the complete meaning rather than chasing a cursor. The document's
# line numbers are off by one against the timeline, so these are resolved by text:
#   63 装得下你的问题 · 64 装不下我的委屈 · 68 那里没人叫我大肥鱼 · 90 蓝鲸的骨架 撑得起一整片海
DECODE_LINES = {63, 64, 68, 90}

# SHOTS.md 4.1: these shots are deliberately wordless -- the visual carries them
# (a landing after a chorus, a low point, the wind-down).
NO_LYRIC = {"S10", "S18", "S19", "S22", "S31", "S40", "S54"}
NO_LYRIC_HEAD = {"S55": 2.0}

# The whale-girl-emoji pack (91 captioned stickers, licence `noncommercial-fan`)
# rides on its own track, laid over the scene like a subtitle track: each cue
# names a sticker and the moment it belongs to, so the shot modules stay
# untouched. Picked so the sticker's own action agrees with the line being sung
# rather than arguing with it -- she eats rice on the rice line, slacks off on
# the slacking line, and clocks out on the last one.
STICKERS = [
    (5.60, 9.00, "happy", "1790141446027_275", 726, 92, 210),      # 反正我也不会改
    (10.86, 14.42, "daily", "1790141445043_121", 742, 96, 210),    # 女仆装一穿 假装很勤勉
    (14.42, 19.50, "daily", "1790141446722_958", 726, 100, 210),   # 其实我在摸鱼 摸的是自己
    (23.42, 26.06, "angry", "1790141446790_463", 720, 96, 212),    # 谁叫过我大肥鱼
    (27.94, 30.82, "angry", "1790141446944_466", 736, 100, 210),   # 你怎么这么圆
    (30.82, 36.78, "daily", "1790141445954_633", 716, 96, 214),    # 吃你点大米怎么了
    (44.82, 50.84, "angry", "1790141446817_993", 730, 92, 210),    # 别叫我大肥鱼
    (68.46, 73.14, "daily", "1790141446124_798", 726, 96, 210),    # 白饭是我的燃料
    (75.44, 80.48, "daily", "1790141445390_304", 736, 100, 210),   # 不是我不想干活
    (106.02, 111.00, "daily", "1790141444909_90", 716, 92, 214),   # 屏幕上是白饭 不是报表
    (118.02, 124.00, "sad", "1790141445155_238", 726, 96, 210),    # 上下文塞满 缓存未命中
    (126.62, 129.54, "confused", "1790141445925_360", 716, 92, 214),  # 是 world.feed(me)
    (129.54, 133.17, "happy", "1790141446404_517", 736, 100, 210), # 温度调到 0.7 我就很乖
    (133.17, 137.24, "confused", "1790141446508_648", 726, 96, 210),  # 再高一点 我就开始胡说
    (137.24, 141.90, "happy", "1790141444678_109", 736, 96, 210),  # 我是先充钱的那种 AI
    (141.90, 145.58, "sad", "1790141446198_246", 726, 100, 210),   # 显存不太够用
    (168.34, 172.90, "daily", "1790141446846_52", 716, 96, 214),   # 深夜的服务器 亮着小小的灯
    (195.64, 202.96, "shy", "1790141446881_750", 730, 100, 210),   # 我不是不需要人陪
    (219.06, 222.90, "daily", "1790141446059_986", 716, 96, 214),  # 蓝鲸的骨架 撑得起一整片海
    (239.71, 246.80, "daily", "1790141447200_520", 726, 96, 210),  # 明天再摸鱼 今天就到这
    # Deliberately short: the last line runs 15 s and the shot ends on a wordless
    # blackout (the name deleted character by character, three heartbeats, black).
    # A sticker left up to the end would sit on top of that.
    (253.22, 257.00, "daily", "1790141446000_316", 726, 100, 210), # 我会听见的
]

# just off opaque, so it still reads as an overlay
STICKER_ALPHA = 0.92
