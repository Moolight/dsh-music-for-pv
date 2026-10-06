# 音乐制作

《请叫我 DeepSeek》这首歌是怎么来的。**全曲由 AI 生成**——作曲、编曲、演唱都是
[YuE2](https://github.com/multimodal-art-projection/YuE) 3B 出的，人做的是写词、
写风格提示、调参数、以及在生成结果里挑。

歌词、LRC、逐词时间在上一层的 [`input/`](../input/README.md)，那是音乐和片子两条流水线
之间共用的接口。

## 流程

```
brief.md          需求书：角色设定、声线、梗句清单、初版歌词框架
     ↓
style.txt         YuE2 的风格提示（爵士 city-pop / 烟嗓萝莉 / 100 BPM / A 小调）
     ↓
workflow/         ComfyUI 工作流 -> YuE2 3B 生成
     ↓
input/song.flac   成品音频
     ↓
scripts/          歌词长度预算、Whisper 转写、LRC 对齐、对齐审计
     ↓
input/lyrics.lrc + input/whisper_words.json
     ↓
chords.abc        和弦谱（注意：是从成品反推的，不是创作输入）
RECORD.md         生成记录与对齐审计报告
```

## 文件

| 文件 | 说明 |
|---|---|
| `brief.md` | 需求书。人写的部分主要在这里 |
| `style.txt` | 喂给 YuE2 的风格提示 |
| `chords.abc` | 和弦谱。**SheetSage2 从成品音频转录出来的**，`Dmaj7\|Gmaj7\|Em7\|A7`、99 BPM、D 大调 |
| `RECORD.md` | 生成记录，含整句核对（LRC 到底对不对得上） |
| `workflow/` | ComfyUI 工作流与构建/运行脚本 |
| `scripts/` | 歌词预算、转写、LRC 对齐与审计 |

## 生成参数

| 项 | 值 |
|---|---|
| 模型 | `yue2_3b_int8_convrot`（YuE2 3B int8） |
| 模式 | `full`（旋律与伴奏一起出） |
| 参考谱面 | **空**——纯生成，不吃参考 ABC |
| seed | 424242 |
| 采样 | temperature 1.0 · top_p 0.95 · top_k 100 · cfg 1.0 |
| `repetition_penalty` | **1.35** |

`repetition_penalty` 是调出来的：1.2 时从 61 秒起掉进循环，同一段主题重复四遍、
Bridge 之后的内容整个丢掉；1.35 才正常走完。

## 为什么不用参考谱面

先试过"喂原曲 ABC、套旋律填新词"这条路（cover 路线），结果是**新词被唱得糊成一团**。
根因不是模型不行：ABC 是从原曲转录的，它的音符时值编码的是**原词**的音节数，
新词的音节对不上就只能拉伸、压缩、吞词。**"保留原曲旋律"和"把新词唱清楚"是互斥的**，
去掉 ABC 就正常了。这一条在 `RECORD.md` 里有完整记录。

## 中文唱词的对齐

这是这部分最花力气的工程。`scripts/` 里三个脚本串起来：

1. `whisper_transcribe.py` —— faster-whisper 转写。**必须 `--no-vad`**：
   开了 VAD，唱段会被整段吞掉，之后所有时间戳全错。
2. `build_lrc_from_whisper.py` —— 逐行 LRC + Whisper 逐词戳 → 逐词时间轴。
   关键点是**词级匹配要按拼音比，不能按字形比**：中文 ASR 的错误绝大多数是同音字
   （鱼/雨、上/伤、鲸/金），按字形比会系统性地丢锚点。
3. `audit_lrc.py` —— 把"字幕对不对得上"拆成两个可证伪的问题：时间轴整体偏没偏
   （全局偏移扫描）、每一句有没有放错位置（本地相似度 vs 全曲最佳位置）。

跑完的结果：**101/103 行（98%）落在正确位置，0 处明显错位，全局最佳偏移 +0.0 秒**。
修之前是 83%、3 处错位。

## 这一节不包含什么

- **音频**：成品和参考曲都不在仓库里，自己生成或自备。
- **Whisper 模型权重**：`fetch_whisper_model.py` 会去下（用了 hf-mirror 镜像，
  并带浏览器 UA——huggingface.co 直连超时、默认 UA 会被 403）。
- **几个环境专用脚本**：`sandbox_patch.py` / `pip_run.py` 是给 Windows 文件沙箱打补丁的
  （`os.mkdir(mode)` 不是 `0o777` 时不会继承父目录的安全描述符，`tempfile.mkdtemp`
  传 `0o700` 会得到一个写不进去的目录），普通机器上不需要。
- **另一首歌的材料**：这个目录里只放《请叫我 DeepSeek》的。早先那首
  Know My Name 的探索过程不在仓库里。

## 署名

作词（改编/扩写）与风格提示、参数调校是本项目做的；**作曲、编曲、演唱是 YuE2 生成的**。
完整署名见 [`../CREDITS.md`](../CREDITS.md)。
