"""The rice odometer: how much she ate across the film.

S06 already puts a real figure on screen -- a `rice_bin` panel whose counter is
`1 + int((t - 30.82) * 13)` grams, captioned `rice/sec 13.0` and `stolen=NNg`.
That is the film's own stated rate, and this module takes it as the anchor.

The other shots where rice appears (the bowl back in her hand, the bowl feeding
the energy column, the rice-and-code band, the empty bowl in S40) have no counter
of their own, so they are given rates here. That is a choice, not a measurement --
but it is made once, in one table, and the running readout the film displays is
computed from it, so the number on the end card is the number the film showed.

    rice.total(268.4)   -> grams eaten by the end
    rice.rate(t)        -> grams per second right now (0.0 outside a window)
"""
from __future__ import annotations

# (t0, t1, grams/sec, what is happening, whether the film states this rate)
WINDOWS = [
    (30.82, 36.78, 13.0, "rice_bin", True),    # the film's own caption: rice/sec 13.0
    (36.78, 40.00, 4.0, "bowl", False),        # the stream returns to her hand
    (68.46, 73.14, 6.0, "fuel", False),        # 白饭是我的燃料
    (75.44, 80.48, 2.0, "slack", False),       # 不是我不想干活
    (118.02, 124.00, 1.5, "cache", False),     # 脑子有点乱 token 在烧
    (137.24, 141.90, 1.0, "charge", False),    # 我是先充钱的那种 AI
    (168.34, 172.90, 0.8, "night", False),     # 深夜的服务器
    (174.78, 182.64, 2.0, "alone", False),     # 一个人摸鱼 是有点寂寞的
    (239.71, 246.80, 3.0, "offwork", False),   # 明天再摸鱼 今天就到这
]


def rate(t: float) -> float:
    for t0, t1, g, _label, _stated in WINDOWS:
        if t0 <= t < t1:
            return g
    return 0.0


def total(t: float) -> float:
    """Grams eaten by time `t`."""
    acc = 0.0
    for t0, t1, g, _label, _stated in WINDOWS:
        if t <= t0:
            continue
        acc += g * (min(t, t1) - t0)
    return acc


def stated() -> float:
    """How much of the total comes from a rate the film itself puts on screen."""
    return sum(g * (t1 - t0) for t0, t1, g, _l, s in WINDOWS if s)


def active(t: float) -> bool:
    return rate(t) > 0.0


if __name__ == "__main__":
    print("窗口                      rate   小计")
    for t0, t1, g, label, s in WINDOWS:
        if g <= 0:
            continue
        print(f"  {t0:7.2f}-{t1:7.2f}  {label:<8} {g:5.1f} g/s  {g * (t1 - t0):7.1f} g"
              f"  {'（本片明示）' if s else ''}")
    print(f"\n终点 {total(268.4):.0f} g   其中本片明示的 {stated():.0f} g")
