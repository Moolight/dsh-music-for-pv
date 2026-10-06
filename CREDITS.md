# 署名与素材许可

dsh-music-for-pv（《请叫我 DeepSeek》歌 + PV）—— 完整署名链、第三方素材出处与许可。

**发布前请先读第 3 节。** 这片子里有一部分素材是 **CC BY-NC-SA 4.0**（署名 + 非商用 + 相同方式共享），
不是可以随便用的。

---

## 1. 作品

| 项 | 值 |
|---|---|
| 作品 | 《请叫我 DeepSeek》歌 + PV |
| 时长 | 4:28（268.42 秒） |
| 规格 | 1280×720 / 3840×2160，24 fps，BT.709，H.264 / HEVC |
| 性质 | **非官方同人作品**，与 DeepSeek、上善、ZipZipPipe 等权利人无从属或合作关系，未经其认可 |

## 2. 署名

### 音乐

| 署名 | 内容 |
|---|---|
| 作词（原案） | `dsh-music-gen/蓝色大肥鱼之歌.md` 提供的梗句清单与初版框架 |
| 作词（改编 / 扩写） | 叙事重排、删重复梗、补梗、按爵士改写 |
| 作曲 · 编曲 · 演唱 | **YuE2 3B（AI 生成）** |
| 风格提示 · 参数调校 | `bluewhale/style_jazz.txt` |
| 生成工具 | ComfyUI + YuE2（`yue2_3b_int8_convrot`），seed 424242 |

> 全曲由 AI 生成，非真人演唱演奏。作曲与编曲是同一次生成（`mode=full` 同时出旋律与伴奏），
> 因此合并署名。`和弦谱.abc` 的 `Dmaj7 | Gmaj7 | Em7 | A7`（99 BPM / D 大调）是
> SheetSage2 从成品音频**反推**出来的，不是创作输入。

### PV

| 署名 | 内容 |
|---|---|
| 制作（代码 / 镜头 / 剪辑） | dsh 鲸鱼娘（AI 代理），在项目作者指导下完成 |
| 视觉语言与工程基础 | **MisakaZentai** — [world-execute-me-dsh-pv](https://github.com/MisakaZentai/world-execute-me-dsh-pv) 的 `tuikit.py` 与 TUI 引擎 |
| 镜头设计 | 57 个镜头，含 7 个视觉母题（被划掉的名字 / 白饭是燃料 / 两个自己 / token 计数器 / 量化 / 参数面板 / 心跳光标） |
| 字幕 | 逐字跟唱高亮；时间轴来自逐行 LRC + Whisper 逐词时间戳 |

**待填**：项目作者的公开署名（昵称 / 主页）——发布前补进上表。

## 3. 第三方素材与许可

### 3.1 角色形象「鲸鱼娘」（CC BY-NC-SA 4.0）⚠

片子里**所有**她的形象都基于这条创作链，按 CC BY-NC-SA 4.0 必须**完整保留署名链**：

1. **一创**：上善 —— 鲸鱼娘角色形象原作者
   <https://www.pixiv.net/users/62155430> · <https://space.bilibili.com/4456176>
2. **二创**：ZipZipPipe（zipzip）—— 加入 DeepSeek 元素的女仆鲸鱼娘二次设计（生成模型 GPT Image 2）
   <https://www.pixiv.net/users/18604994> · <https://space.bilibili.com/4168597>
3. **三创**：Small-tailqwq / dsh-deep-whale —— 本片使用的立绘
4. **八种表情**：dsh-whale-galgame <https://github.com/JAdpp/dsh-whale-galgame>

- 来源：`film/third_party_references/whale_maid_expanded_20260926/`，许可全文在 `dsh-pv/LICENSES/CC-BY-NC-SA-4.0.txt`
- **条款**：署名、**不得商用**、改编作品须以相同方式共享
- **本片做了什么**：裁切、缩放、像素化、半调点阵化、调色、表情合成

> ZipZipPipe 的 [Pixiv 原帖](https://www.pixiv.net/artworks/148186519) 要求署名 + 非商用，
> 并说明 DeepSeek 娘遵循上善的 CC BY-NC-SA 4.0。**该条款不适用于该作者的其他角色。**

### 3.2 表情包「鲸鱼娘表情包」（noncommercial-fan）

- 用于片中的 21 处贴纸，走独立的一轨
- 包 ID：`whale-girl-emoji`（91 张，6 个情绪分类）
- **作者 / 维护者**：Luocheng114
- **许可**：`noncommercial-fan` —— **仅限非商业使用**
- **上游来源**（包里自述）：
  - 女仆 44 张，来自 `dsh-maid-emoji` 内置包
  - 大肥鱼 47 张，来自 `EDMOK/blue-fish-archive`
- 分发：`yyh-001/dsh-meme-packs` 的 release
  <https://github.com/yyh-001/dsh-meme-packs>
- 本机路径：`~/.dsh/meme-packs/whale-girl-emoji/`

> **为什么用这个而不是 `deepseek-chan`**：那个包 128 张、台词更密集，但**没有附任何许可声明**；
> 这个包在 `manifest.json` 里明确写了 `license: noncommercial-fan` 和维护者。
> 片子本来就是非商用（见 3.1 的 CC BY-NC-SA 4.0），两者不冲突。
>
> **改动**：只做了一件事——把平底抠成透明（从边界泛洪填充，保住贴纸自带的中文台词）。
> 抠图后贴纸不再是挡住画面的白卡，而是角色本身浮在场景里。原图未做任何其它修改。

### 3.3 DeepSeek 名称与标识

- S36/S37「幻觉里我是一条真的鲸鱼」用的是 **DeepSeek 官方鲸鱼标**
- 仓库里带了两份，出处与许可见 [assets/README.md](assets/README.md)：
  `deepseek-logo.svg`（`@deepseek-ai/dsh-web-frontend`，MIT）和
  `dsh-logo.png`（`@michengai/dsh-skills-manager`，Apache-2.0）
- **MIT 和 Apache-2.0 都不包含商标**：DeepSeek 的名称和标识归其权利人所有
- 本片是致敬性质的同人创作，不代表 DeepSeek 官方

### 3.4 上游仓库的代码与字体

| 素材 | 权利人 / 许可 |
|---|---|
| `tuikit.py`、TUI 引擎等（**不在本仓库，需自行 clone**） | MisakaZentai，**MIT** |
| Space Mono Bold、Anton Regular（随上游仓库） | **SIL Open Font License 1.1** |
| Consolas、微软雅黑、Segoe UI Symbol | Windows 自带，**未随片分发** |
| dsh 前端 CSS / JS（上游 vendored） | MIT，Copyright (c) 2026 DeepSeek |

> 本片**没有**使用上游的 dsh 聊天窗口那一半（只做了右边），但复用了它的
> `tuikit.py` 视觉语言与配色体系。

### 3.5 未使用的

- `assets/comfyui/` 那套 chibi 立绘（`out-chibi*`、`out-qwen` 等）—— 做过处理实验（`chibi.py`），
  **最终片子里没有采用**，被表情包方案取代。
- 上游原片的舞者画面（第三方 MMD 模型与动作，许可范围未确认）—— 未使用。

## 4. 发布前检查清单

- [ ] 完整保留 3.1 的**四段署名链**
- [ ] 标注「**非官方同人作品**」
- [ ] 标注「**AI 生成**」（音乐 YuE2 + PV 代码渲染）
- [ ] 确认**非商用**（CC BY-NC-SA 4.0 + 表情包的 `noncommercial-fan`，两条都锁死非商用）
- [ ] 本片衍生部分按 CC BY-NC-SA 4.0 分享
- [ ] 署名表情包维护者 **Luocheng114**（`whale-girl-emoji`，`noncommercial-fan`）
- [ ] 补上项目作者的公开署名

## 5. 本 PV 工程自己的代码

本 PV 的代码（`pv.py`、`shotkit.py`、`scenes.py`、`shots_g1..g5.py`、`timeline.py`、
`sticker.py`、`logo.py`、`encode_pv.py` 等）为本项目新写。**但成片整体按 CC BY-NC-SA 4.0 分享**，
因为其中包含上述角色形象的衍生画面。
