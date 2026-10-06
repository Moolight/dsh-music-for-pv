# dsh-music-for-pv

## 《请叫我 DeepSeek》

一支歌和它的 PV 的全部制作代码。两部分：

- **`music/`** —— 歌是怎么生成的。词、风格提示、ComfyUI 工作流、LRC 对齐与审计。
  作曲 · 编曲 · 演唱由 **YuE2 3B** 生成。
- **根目录** —— PV 是怎么渲染的。每一帧都是歌曲时间 `t` 的纯函数，
  24 fps，1280×720（另出 4K）。正片 4:28，带片头制作信息和片尾授权信息。

两条流水线是分开的：`music/` 出音频和歌词时间，交给 PV 当输入。
**换掉 `content/` 就能拿这套引擎做另一支片子**，`pvlib/` 一行都不用动。

PV 的视觉语言来自
[world-execute-me-dsh-pv](https://github.com/MisakaZentai/world-execute-me-dsh-pv)（MisakaZentai，MIT）
的 `tuikit.py`——原版是把 dsh 聊天窗和模型可视化拼在一起的双屏片，
**这一版只做右边**，也就是"她所在的那个世界"。工具箱已 vendor 进 `pvlib/vendor/`，
克隆下来就能跑，不需要先 clone 上游。

---

## 这个仓库里没有什么

先把话说前面，免得你克隆下来跑不动：

| 缺的东西 | 为什么 | 你自己怎么补 |
|---|---|---|
| **成片** | 里面有角色立绘，按 CC BY-NC-SA 4.0 **不得商用、须署名、须相同方式共享**，不适合塞进代码库 | 自己跑一遍，或者找作者要 |
| **音频**（成品歌） | 同上的考虑，而且 27 MB | 按 [`music/`](music/README.md) 自己生成，或自备 |
| **歌词 / 逐词时间** | 与歌同源，随歌一起 | 放进 `input/`，见 [input/README.md](input/README.md) |
| **表情包** | 是装在本机的 DSH 表情包（`noncommercial-fan`） | 装 DSH 表情包，或用你自己的图 |
| **Windows 系统字体** | Consolas / 微软雅黑是系统自带，随仓分发不合规 | Windows 上有；其它系统用 `PV_F_*` 指过去 |

**代码是 MIT，但成片不是。** 成片里含角色美术，归 CC BY-NC-SA 4.0。

## 你要准备什么

- Python 3.11+，`pip install -r requirements.txt`（其实主要就 Pillow）
- **ffmpeg**（在 PATH 里）
- 歌、歌词、逐词时间，放进 `input/`。**歌可以自己生成**——见 [`music/`](music/README.md)
- Windows 字体（或设 `PV_F_MONO` / `PV_F_CJK` / `PV_F_SYM` 指到别的等宽和 CJK 字体）

**工具箱、字体、角色立绘都已经随仓携带**（`pvlib/vendor/`、`assets/`），
所以不需要 clone 上游仓库就能跑。想改工具箱本身的话再设 `PV_TUI` 指向上游克隆。

```bash
python -m pvlib.config     # 自检：把缺的东西列出来
```

字体默认取 Windows 的 Consolas（等宽）和微软雅黑（中文）。其它系统用
`PV_F_MONO` / `PV_F_CJK` 指过去——上游 `docs/FONTS.md` 有替代字体的说明。

```bash
export PV_TUI=/path/to/world-execute-me-dsh-pv/film/tui_pv_world_execute_20260926
python config.py          # 自检：把缺的东西列出来
```

## 跑

```bash
python timeline.py                          # 歌词 + LRC + Whisper 逐词 -> out/timeline.json
python render.py all --workers 14           # 全片 -> out/frames/
python cards.py head out/cards_head         # 片头卡
python cards.py tail out/cards_tail         # 片尾卡
python encode.py out/frames --song input/song.flac --out out/film.mp4 \
       --head out/cards_head --tail out/cards_tail --4k
```

渲一小段来审：

```bash
python render.py strip 43.76 53.76 --out out/review --sheet out/sheet.png
python render.py range 158.2 164.3 --workers 14   # 只重渲某一段
python render.py sheet --out out/review           # 只重出接触表
python tools/make_sample.py --at 43.76 --dur 10   # 渲一段 + 配对应音频，出 mp4
python tools/check_shots.py                       # 每个镜头抽一帧，拼总览
python tools/place_stickers.py --report           # 重算贴纸避让位置
python tools/survey_stickers.py --list            # 看装了哪些表情包
```

`tools/check_shots.py` 值得先跑一次：它会渲染全部 57 个镜头各一帧，
**有镜头崩了会直接告诉你**，比铺满全片再发现便宜得多（开发时就靠它一次抓出 6 个会崩的镜头）。

## 配置

外部资源一律走环境变量，不写死在代码里（[config.py](config.py)）：

| 变量 | 默认 | 说明 |
|---|---|---|
| `PV_TUI` | `../film/tui_pv_world_execute_20260926` | tuikit 引擎所在目录 |
| `PV_MEME_PACKS` | `~/.dsh/meme-packs` | DSH 表情包根目录 |
| `PV_STICKER_PACK` | `whale-girl-emoji` | 用哪个包 |
| `PV_SONG` / `PV_LYRICS` / `PV_LRC` / `PV_WHISPER` | `input/*` | 你自己的素材 |
| `PV_COMFY_ART` | 未设 | 只有 `chibi.py` 用，成片没用到 |
| `TUI_PALETTE` | `deepsea` | tuikit 的调色板，`shotkit` 会锁死 |

## 代码结构

两部分：**音乐**（`music/`）和 **PV**。PV 又分成三层：引擎（可复用）、内容（这一支片子）、工具。

```
music/               歌是怎么来的——见 music/README.md
  brief.md           需求书：角色设定、声线、梗句清单
  style.txt          YuE2 风格提示
  chords.abc         和弦谱（从成品反推，不是创作输入）
  RECORD.md          生成记录与对齐审计
  workflow/          ComfyUI 工作流 + 构建/运行脚本
  scripts/           歌词预算、Whisper 转写、LRC 对齐与审计

render.py            PV 接线 + CLI：把各层按顺序叠起来，内容从 content/ 注入
encode.py            帧序列 + 歌曲 -> BT.709 mp4（含片头片尾拼接与音频延迟）
cards.py             卡片渲染器（吃什么 spec 画什么）
cover.py             封面：1280×720 与 4K，`--scale 3`
timeline.py          歌词 + LRC + Whisper 逐词 -> out/timeline.json

pvlib/               PV 引擎——不认识这一支片子
  config.py          外部资源路径，全部可用环境变量覆盖
  kit.py             共享绘图接口：Shot、缓动、中文文字、面板、立绘、清场
  band.py            LyricBand：底部字幕带，逐字跟唱高亮
  overlays.py        StickerTrack / RiceMeter：按时间码叠的轨道
  scenes.py          按时间把镜头分派给内容层的 act 模块
  assets/
    stickers.py      表情包读取与抠底
    logo.py          DeepSeek 鲸鱼标 -> 剪影/描边/柔光

content/             PV 这一支片子的全部内容
  cues.py            贴纸时间码 / 无字幕镜头 / 整句 decode 行
  credits.py         片头片尾文案
  rice.py            白饭里程表的窗口与速率
  acts/act1..5.py    57 个镜头的实现
  SHOTS.md           镜头表：时间窗、覆盖行号、画面描述与意图

tools/               审片与素材工具（不属于渲染路径）
docs/cjk-notes.md    tuikit 的中文字号/后期实测数据
```

**想拿这套做自己的片子，只需要换 `content/`**：改 `cues.py` 的时间码和文案、
`acts/` 里的镜头、`credits.py` 的署名，引擎一行都不用动。
`pvlib/` 里的东西和这一首歌没有任何耦合——它只认时间轴、镜头表和几张 cue 表。

## 怎么做的

**纯函数。** 每个镜头是 `t` 的函数，没有跨帧状态，所以帧可以乱序、可以分块并行。
唯一的例外是后期残影（`post(trail)` 要上一帧），所以并行是按**连续片段**切，
每块各自带自己的历史。

**字幕。** 主体是逐字跟唱高亮：没唱到的字暗着占位，唱到哪个字哪个字亮成品牌蓝。
逐字时间由 Whisper 的逐词戳摊到行文本上——**不能按字形匹配**，因为中文 ASR
返回的多半是同音字和繁体（別/飛/魚），按位置比例对齐才能同时扛住简繁不一致、
词被吞掉、词数不等。

四个语义转折点例外，改成整句从噪点里 `decode` 出来，让观众读到完整意思。
八个镜头整镜不出字幕（纯视觉，约 46 秒）。一句唱完保持 0.35 秒再整体淡出。

## 给别人复用的坑

这些都是踩出来的，不是推测。按重要性排：

**1. `tuikit` 的 `banner_block` 只能画拉丁字母。** 喂中文不报错、不空白，
而是安静地画出**豆腐方框**（Anton 字体没有汉字 → FreeType 回退 `.notdef`）。

**2. 暗角会压死底部字幕带。** `vignette` 默认 `LYRIC_LIFT=False`，
18px 白字在 y=660 的墨量从 1320 掉到 297、蓝色的只剩 91/1169。
`shotkit` 在 import 时就把 `LYRIC_LIFT[0] = True` 锁死。

**3. `post()` 的 trail 是重影元凶。** 它是"取亮"叠加＝上一帧双重曝光，
`(0.42, 0.35)` 下 18px 中文读不出来。定在 `(0.12, 0.10)`。

**4. 中文字号下限 18px。** 14px 笔画只剩 1px，「海/鲸」这类字内脏会并笔。
正文 24px、标题 32px。**文字压在立绘或热图上必须垫板**（`slab_text`），
否则被底下的亮像素吃掉。

**5. 白底贴纸直接叠上去就是一张不透明的卡。** 它会把画面挡掉。正确做法是
从边界泛洪填充把平底抠掉——而且**要从所有边界像素起填，不是只从白的**，
因为约三分之一的贴纸是深色底，只喂白色会留下一圈黑框。贴纸自带的中文台词
是独立连通块，所以抠底时不会丢。

**6. 判断"这里能不能放东西"不能用亮度阈值。** 这类画面里全是**暗而存在的面板**
（一个缓存矩阵格子的亮度只有 65 左右），阈值法会把它们当成空的。

**7. ffmpeg 的 image2 解复用器默认从第 0 帧找起。** 帧号是全局帧号，
所以要传 `-start_number`，否则报 `Could find no file ... index in the range 0-4`。

**8. `-vf` 和 `-filter_complex` 不能同时给同一个输出流。** 要缩放又要拼接，
`scale` 必须并进滤波图里。

**9. 某些环境禁命名管道**，Windows 的 `multiprocessing` 会直接 `WinError 5`。
`pv.py` 因此用**线程池**（PIL 的 C 调用释放 GIL，6441 帧约 3 分钟）。这一条只在
沙箱里会遇到，普通机器上用进程池更好。

**10. 4K 用 Lanczos，不要用最近邻。** 上游那版选最近邻是因为它全片是像素艺术；
这片子大半时间画面里是中文小字，最近邻会把 24px 汉字放大成一格一格的锯齿。
1280×3 = 3840 正好整数倍，Lanczos 出来的字是干净的。

## 未做

- 左侧的 dsh 聊天窗口（这一版只做右边）。
- 合唱和声、淡出只能在风格提示里要求，无法验证。
- S36/S37 那条"真鲸"用的是 DeepSeek 官方标识，抠图后走半调点阵。
  那张 PNG 抠起来要**同时满足不透明和暗**两个条件：文件是浅色圆角底板
  （不透明）＋黑色鲸鱼＋底板外围半透明阴影，只看 alpha 会连底板一起选中、
  只看亮度会连阴影一起选中。

## 许可

- **代码**：MIT（[LICENSE](LICENSE)）
- **成片**：CC BY-NC-SA 4.0（含角色美术，署名·非商用·相同方式共享）
- **上游引擎**：MIT，MisakaZentai
- 完整署名链、表情包许可、商标说明：[CREDITS.md](CREDITS.md)

这是**非官方同人作品**，与 DeepSeek 及 CREDITS 里列出的各位作者无从属或合作关系。
DeepSeek 的名称与标识归其权利人，MIT 许可不包含商标。
