# tuikit 中文可用性验证报告（deepsea 调色板）

验证对象：`film/tui_pv_world_execute_20260926/tuikit.py`（476 行，纯 PIL，1280x720）
验证方式：渲染 20+ 张测试帧后**逐张肉眼查看**（含 2x/3x 最近邻放大对照），附像素级指标。
所有帧都在 `out/`，报告文件 `out/report_probe{,2,3,4,6}.txt`。

---

## 结论速览

| 问题 | 结论 |
| --- | --- |
| 中文字号 | **24px 主力歌词、18px 下限、32px 标题/大字、14px 仅限不叠图的短注解** |
| post() 安全值 | **trail 0.10~0.15 + bloom 0.08~0.12（推荐 0.12/0.10）**，禁用 (0.42,0.35) 叠中文 |
| 中文字色 | **叙述用 UI（冷白钢 200,214,234）；她的声音用 BLUE_TEXT（120,148,255）；BLUE_MID 只给图形** |
| 立绘尺寸 | **用 halfblock，bust 裁切 max_w≈620 → 620x552；400x360 是下限；≤300x264 糊** |
| banner_block | 拉丁字母=像素块字（好看）；**中文=豆腐块**（不崩、不空白，画成 notdef 方框） |

---

## 一、中文字清楚到什么程度

`msyh.ttc`（微软雅黑）实测（同句「请叫我 DeepSeek」/「深海里的鲸鱼娘」）：

| 字号 | bbox | 墨量 | 目视判断 |
| --- | --- | --- | --- |
| 14px | 114x14 / 98x13 | 440 / 467 | 笔画只有 1px，`海/鲸`这类字的内脏开始并笔；1x 还能读，3x 放大可见结构性糊 |
| 18px | 145x19 / 126x19 | 659 / 771 | 干净、稳，**歌词可用的下限** |
| 24px | 195x26 / 168x23 | 1324 / 1504 | 舒服，主力歌词字号 |
| 32px | 257x35 / 224x32 | 2242 / 2440 | 大字/标题，笔画之间留白充裕 |

- 证据帧：`probe_sizes_1x.png`（1x 原生大小）、`probe_sizes_zoom3x.png`（3x 放大看笔画）
- 14px 在 1x 下"能读但吃力"，蓝色 14px 更吃亏（见第三节）
- 微软雅黑对全部测试字串**零豆腐块**，标点、`「」`、逗号、句号都正常

## 二、post() 对中文小字的影响

`post(img, prev, trail, bloom)` = 残影(取亮) + 加性辉光 + 扫描线 + 暗角。

- **trail 是主要杀手**：残影是"取亮"叠加，等于把上一帧的字**双重曝光**在当前帧上。
  - (0.42,0.35)：18px 那行中文在 2x 放大下彻底变重影，读不出来（`probe_post_grid.png` 第 1 行）
  - (0.30,0.20)：重影仍明显
  - (0.20,0.10)：只剩淡淡一圈边，可读
  - (0.00,0.00)：干净
- **bloom 是加性**（`ImageChops.add`），会整体抬起黑底 → dot_field 的噪点变成可见的雾，笔画发虚。0.35 时 18px 明显发毛。
- **扫描线固定吃掉约 15% 行**（3px 一条、alpha 55）：18px 墨量 1143→1021，14px 666→561。
- **推荐值：`post(img, prev, 0.12, 0.10)`**，且中文在场时 `prev` 尽量给 None；
  需要最锐利时干脆不用 post，自己叠 `tk.scanlines()` + `tk.vignette(True)`
  （对照：`probe_recipe.png` 有奶雾感 vs `probe_recipe_crisp.png` 干净）。
- 参数对照帧：`probe_post_grid.png` + `probe_post_t042_b035/t030_b020/t020_b010/t000_b000.png`

## 三、deepsea 下中文字该用什么颜色

| 颜色 | RGB | 亮度 | 目视 |
| --- | --- | --- | --- |
| `UI` | (200,214,234) | 212 | 最清楚，冷白钢；**叙述/系统/歌词正文用这个** |
| `BLUE_TEXT`(代码里的 ME_TEXT) | (120,148,255) | 152 | 24px 清楚、18px 可用，post 后带一层蓝晕很有"她的声音"味 → **她的台词/歌声** |
| `BLUE_MID`(代码里的 ME_MID) | (77,107,254) | 115 | 太暗：18px 中文字开始糊成一团 → **只给 dot_chart / box / heat 这类图形** |

证据帧：`probe_text_color.png`（6 组：3 色 × 原始/加 post）

## 四、立绘在 1280x720 占多大

- **halfblock（推荐）**，bust 裁切（`CROPS["bust"]`，源图 636x571，h/w=0.898）：
  - `max_w=620,max_h=700` → **620x552**：一眼认出鲸鱼娘（发箍、双马尾/呆毛、眼睛、腮红、女仆头饰），占画面约一半宽，最合适
  - `max_w=400,max_h=460` → 400x360：还能认出，五官开始糊（可用下限）
  - `max_w=300` → 300x264 / `max_w=220` → 220x192：脸部塌成噪点，不可用
  - 注意：**高度是被 aspect 卡住的**（620x700 → 552 高），不是你说多少就多少
  - 证据帧：`probe_sprite_halfblock.png`、`probe_halfblock_scale2.png`、`probe_halfblock_big.png`
- **glyph_sprite（慎用）**：出来的东西更像"戴兜帽的锥形剪影"，不像鲸鱼娘，边缘描边字符（`/ \ | -`）让画面很吵。
  - 关键坑：字符单元是 `cw x round(1.15*size)`，**宽高比约 1:2**，函数**不做比例校正**，
    直接用 `cols:rows = 1:1` 会纵向拉伸近 2 倍（我第一次 bust 40x34 就是这样歪的）。
  - 正确公式：`rows = cols * (src_h/src_w) * cw/ch`（size=10 时 cw=6,ch=12 → 系数 0.5）
  - 裁切源比例：full 1.94 / upper 1.056 / bust 0.898 / face 0.806
  - 比例修正后可用组合：bust 64x29 → 386x348；bust 92x41 → 554x492；full 66x64 → 332x640
  - 证据帧：`probe_sprite_glyph.png`（歪的）vs `probe_sprite_glyph_aspect.png`（修正后）

## 五、banner_block 与中文

- 拉丁效果：Anton 字形被量化成**像素块马赛克**，每 8px 一格带深色格缝（`grid_mask`），
  "终端像素大字"的味道很足 —— 拿来打 `DEEPSEEK` 很好看（`probe_a.png` 顶部）。
- **中文：不会崩、不会空白，会画成豆腐块。** Anton 没有汉字，FreeType 回退到 `.notdef`，
  每个汉字变成一个空心方框。
  - `banner_bits('请叫我')` → cells (30,18)、非零像素 380（**不是全黑**，所以不会触发"空白"兜底）
  - `banner_bits('鲸')` → (9,18)、非零 122
  - 混排 `请叫我 DeepSeek` → 拉丁部分正常，汉字部分三个方框（`probe_banner_cjk.png`）
  - 也就是说这活儿**不会报错**，只会安静地端上一排方框，很危险
- 结论：`banner_block` 只用 ASCII；中文用 msyh 画在它下面/旁边（`probe_a.png` 就是这样，协调）

---

## 六、没被点名但会咬人的坑

1. **`box()` 标题画不出中文**：标题字体是 SpaceMono-Bold，写 `box(..., "系统日志")` 会变成 5 个豆腐框。
   → 标题用 ASCII，中文标签自己用 msyh 画在面板内部。证据：`probe_box_title_cjk.png`
2. **`LYRIC_LIFT` 默认 False，暗角把底部歌词带压死**（这是最大的坑）：
   18px 白字墨量随 y 衰减 —— y=200:1107、y=400:1167、y=560:887、
   **y=610:621、y=660:297**；蓝色更惨，y=610 只剩 **91/1169**。
   渲染前 `tk.LYRIC_LIFT[0] = True` 后：y=610:1089、y=660:1121、y=690:1669。
   → 底部歌词带必须开 `LYRIC_LIFT`。证据：`probe_vignette.png` + `report_probe3.txt`
3. **暗角同样压顶部角落**：y=60 的 18px 白字墨量 1320→476（掉 64%）。重要文字尽量放画面中部。
4. **中文压在 halfblock 立绘上会被吃掉**：立绘是亮而密的像素材质，白字叠上去直接糊没
   （`probe_overlay_no_slab.png` 里 32px 的「深海里的鲸鱼娘」已读不出，18/14px 全废）；
   在文字下垫一块纯 BG 矩形（`d.rectangle(..., fill=tk.BG)`）就完全清楚
   （`probe_overlay_slab.png`）。→ **文字要压图必须垫板**。
5. **导出名不是 ME_***：tuikit 导出的是 `UI / ERR / ANOM / BLUE_LO / BLUE_MID / BLUE_HI / BLUE_TEXT`；
   没有 `ME_TEXT`/`ME_MID`（第一次跑就 AttributeError）。调色板靠 `TUI_PALETTE` 环境变量在 import 前设置。
6. **必须从原路径 import**：`sprite_src` 用 `Path(__file__).parents[1]` 定位素材，复制 tuikit.py 到别处就找不到立绘/字体。
7. **`decode()` 能用于中文**：按字符计时，settle 期闪的是 ASCII 噪声字符（`SCR`），
   所以汉字解码时会闪现 `% - = $ <`；rate=45 对中文太快（18 字 ≈ 0.4s），建议 12~18。
   证据：`probe_decode_cjk.png`
8. **`tokenize()` 对中文天然友好**：每个汉字一个 token（`['请','叫','我','DeepS','eek']`），
   `token_id` 走 UTF-8+crc32 正常（`请` → 89123）。假 BPE 面板可以直接上中文。
9. `heat_cell` 的 `mix(color, 0.06+0.94v)` 低值几乎压成黑；**别同一张图里换色相**，
   否则"值→颜色"的映射就没了（我在 probe_d 里试过彩虹版，只剩装饰性）。
10. `dot_field(w,h,step)` 返回 `(w, h+step)` 高度，铺满画布要传 `H-16`。

## 七、文件清单

帧（`out/`）：
`probe_a.png` / `probe_a_post.png`（标题卡）、`probe_b.png`（立绘+面板）、
`probe_c.png`（波形）、`probe_d.png`（热图）、`probe_e.png` / `probe_e_raw.png`（合成帧 raw/post 对照）、
`probe_sizes_1x.png` / `probe_sizes_zoom3x.png`、`probe_post_grid.png` + 4 张 post 参数帧、
`probe_text_color.png`、`probe_sprite_glyph.png` / `probe_sprite_glyph_aspect.png`、
`probe_sprite_halfblock.png` / `probe_halfblock_scale2.png` / `probe_halfblock_big.png`、
`probe_banner_cjk.png`、`probe_scanline_cjk.png`、`probe_vignette.png`、
`probe_box_title_cjk.png`、`probe_decode_cjk.png`、
`probe_overlay_no_slab.png` / `probe_overlay_slab.png`（叠字对比）、
`probe_recipe.png` / `probe_recipe_crisp.png` / `probe_recipe_raw.png`（推荐配方）

脚本：`probe_frames.py`（主 5 帧 + 尺寸/颜色/立绘/banner 对照）、`probe_frames2.py`（扫描线/比例）、
`probe_frames3.py`（暗角/box 标题/decode）、`probe_frames4.py`（对比度指标）、
`probe_frames5.py`（推荐配方）、`probe_frames6.py`（叠字垫板验证）
