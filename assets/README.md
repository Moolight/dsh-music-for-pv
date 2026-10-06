# assets/

为让仓库克隆下来就能跑而随仓携带的资源。**都不是本项目的作品**，各自许可见下，
每样都附了原始许可文件。

## `fonts/` — 工具箱用的两款字体

| 文件 | 字体 | 许可 |
|---|---|---|
| `SpaceMono-Bold.ttf` | Space Mono Bold | SIL Open Font License 1.1（`OFL_spacemono.txt`） |
| `Anton-Regular.ttf` | Anton Regular | SIL Open Font License 1.1（`OFL_anton.txt`） |

`tuikit` 用 Anton 画巨型方块拉丁字母（`banner_block`），用 Space Mono 画面板标题。
出处：上游 world-execute-me-dsh-pv 的 `film/ai_mascot_mv_world_execute_20260926/fonts/`。

> **中文不走这两款字体**（它们没有汉字）。中文一律用 Windows 自带的微软雅黑，
> 由 `PV_F_CJK` 指定；等宽用 Consolas（`PV_F_MONO`）。这两款是系统字体，
> **没有随仓分发**——其它系统用 `PV_F_*` 指过去即可。

## `sprites/` — 角色立绘（CC BY-NC-SA 4.0）⚠

| 文件 | 说明 |
|---|---|
| `whale-*.webp` | 8 种表情：cheerful / starry / shy / serious / confused / frightened / angry / exasperated |
| `maid-left.webp` | 女仆装立绘 |
| `galgame-NOTICE.md`、`upstream-NOTICE.txt`、`upstream-LICENSE.txt` | 上游原始许可与署名文件 |

片子里的"她"就是这些图，经 `halfblock` / `glyph_sprite` 处理成半调点阵。

### 署名链（必须完整保留）

1. **一创**：上善 —— 鲸鱼娘角色形象原作者
   <https://www.pixiv.net/users/62155430> · <https://space.bilibili.com/4456176>
2. **二创**：ZipZipPipe（zipzip）—— 加入 DeepSeek 元素的女仆鲸鱼娘二次设计
   <https://www.pixiv.net/users/18604994> · <https://space.bilibili.com/4168597>
3. **三创**：Small-tailqwq / dsh-deep-whale —— 本片使用的立绘
4. **八种表情**：dsh-whale-galgame <https://github.com/JAdpp/dsh-whale-galgame>

许可全文：上游 `LICENSES/CC-BY-NC-SA-4.0.txt`，条款要点见 [`../CREDITS.md`](../CREDITS.md)。

**条款**：署名 · **不得商用** · 改编作品须以相同方式共享。
用这些图渲出来的任何东西都继承这个许可——包括成片。

## `deepseek-logo.svg` / `dsh-logo.png` — 鲸鱼标识

- `deepseek-logo.svg`：`@deepseek-ai/dsh-web-frontend@0.1.5-rc.3` 的 `dist/favicon.svg`，**MIT**
- `dsh-logo.png`：`@michengai/dsh-skills-manager@1.1.9` 的 `assets/branding/dsh-logo.png`，**Apache-2.0**

`logo.py` 读的是 PNG（Pillow 不能光栅化 SVG）。抠图要**同时满足"不透明"和"暗"**
两个条件：文件结构是浅色圆角底板＋黑色鲸鱼＋底板外围半透明阴影，只看 alpha 会连底板
一起选中、只看亮度会连阴影一起选中。

## 商标

**MIT / Apache-2.0 / SIL OFL / CC BY-NC-SA 都不包含商标。**
DeepSeek 的名称与标识归其权利人所有。这里的文件只解决"渲染时需要这枚图形"的问题，
不代表任何授权或关联；本片是非官方同人作品。
