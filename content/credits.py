"""The text of the title card and the end credits.

Content, not engine: `cards.py` renders whatever spec it is handed, so a
different film supplies its own lists here.

A spec is `(title, lines)`, and each line is one of:

    kv(label, value)   a two-column row
    h(text)            a sub-heading
    body(text)         a plain line
    note(text)         a small dim line
    GAP                vertical space
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from content import rice as _rice  # noqa: E402

FILM_END = 268.4
HEAD_DUR = 5.0
TAIL_DUR = 6.0


def kv(label: str, value: str):
    return ("kv", label, value)


def h(text: str):
    return ("h", text, "")


def body(text: str):
    return ("b", text, "")


def note(text: str):
    return ("n", text, "")


GAP = ("g", "", "")

HEAD = ("请叫我 DeepSeek", [
    h("PV"),
    GAP,
    kv("音乐", "作词 · 作曲 · 编曲 · 演唱　YuE2 3B（AI 生成）"),
    kv("PV", "制作 · 镜头 · 剪辑 · 字幕　dsh 鲸鱼娘"),
    kv("", "视觉语言　MisakaZentai / world-execute-me-dsh-pv"),
    GAP,
    note("非官方同人作品 · 全片由 AI 生成"),
])

TAIL = [
    ("音乐", [
        kv("原案", "需求书：DeepSeek 的自我介绍"),
        kv("作词（改编·扩写）", "dsh 鲸鱼娘"),
        kv("作曲 · 编曲 · 演唱", "YuE2 3B（AI 生成）"),
        kv("风格提示 · 参数调校", "dsh 鲸鱼娘"),
        kv("生成工具", "ComfyUI + YuE2"),
        GAP,
        note("全曲由 AI 生成，非真人演唱演奏。"),
        note("和弦谱为 SheetSage2 从成品音频反推，不是创作输入。"),
    ]),
    ("PV", [
        kv("制作", "代码 · 镜头 · 剪辑 · 字幕　dsh 鲸鱼娘（AI 代理）"),
        kv("视觉语言 · 工程基础", "MisakaZentai　world-execute-me-dsh-pv"),
        kv("时间轴", "逐行 LRC + Whisper 逐词对齐"),
        kv("字幕", "逐字跟唱高亮"),
        kv("镜头", "57 个 · 7 个视觉母题"),
        GAP,
        kv("白饭统计", f"全片一共吃了 {_rice.total(FILM_END):.0f} g"),
        note(f"其中 {_rice.stated():.0f} g 按本片刻意给出的计量 rice/sec 13.0 折算，"
             "其余按她每次吃饭的镜头计量。"),
        kv("", "本片没有饿着她。"),
        GAP,
        note("本片只做了原引擎的「右边」——她所在的那个世界。"),
    ]),
    ("角色形象「鲸鱼娘」", [
        kv("许可", "CC BY-NC-SA 4.0　署名 · 非商用 · 相同方式共享"),
        GAP,
        kv("一创", "上善　　角色形象原作"),
        kv("二创", "ZipZipPipe　　加入 DeepSeek 元素的女仆版设计"),
        kv("三创", "Small-tailqwq / dsh-deep-whale　　本片使用的立绘"),
        kv("表情", "dsh-whale-galgame　　八种表情"),
        GAP,
        note("必须保留完整署名链 · 不得商用 · 改编作品须以相同方式共享"),
    ]),
    ("素材与声明", [
        kv("表情包", "whale-girl-emoji　维护者 Luocheng114 · noncommercial-fan"),
        note("女仆 44 张来自 dsh-maid-emoji，大肥鱼 47 张来自 EDMOK/blue-fish-archive"),
        note("包来自 yyh-001/dsh-meme-packs"),
        kv("鲸鱼标", "DeepSeek 官方标识，商标归其权利人所有"),
        kv("字体", "Space Mono / Anton（SIL OFL）"),
        note("Consolas / 微软雅黑 / Segoe UI Symbol（Windows 自带）"),
        GAP,
        note("非官方同人作品。与 DeepSeek 及上述各位作者无从属或合作关系。"),
    ]),
]
