# workflow/

ComfyUI 工作流与两个脚本。工作流是 **API 格式**（`bluewhale_jazz.json`），
可以直接 POST 给 `/prompt`，不需要在界面里手动连线。

```bash
python run_workflow.py bluewhale_jazz.json --host 127.0.0.1:8188
```

`build_workflow.py` 是从 ComfyUI 的 `/object_info` 生成工作流的，
所以它不依赖某个 ComfyUI 版本的节点顺序——节点新增了输入，重新跑一次就同步了。

```bash
python build_workflow.py <seed> <后缀> <最大时长> <""|free> <full|melody>
# 环境变量：KMN_REF  KMN_LYRICS  KMN_STYLE  KMN_TITLE(只能 ASCII)  KMN_STEM
#           KMN_ABCGEN=1  KMN_REP_PEN（默认 1.2）
```

## 节点

| 节点 | 作用 |
|---|---|
| `CheckpointLoaderSimple` | 载入 `yue2_3b_int8_convrot` |
| `YuE2GenerateMusic` | 生成。`mode=full` 出旋律+伴奏；`abc=""` 表示不吃参考谱面 |
| `SheetSage2AudioToABC` | 音频转 ABC 谱面。本片**没有**把它接进生成，只用它反推和弦谱 |
| `EmptyYuE2LatentAudio` / `VAEDecodeAudio` / `SaveAudioAdvanced` | 潜变量、解码、落盘 |
| `SongFilename` | 统一文件名前缀 |
| `SongLyricsToLRC` / `SongSaveMatchingLRC` | 按歌词切 LRC（本片没用，我们的 LRC 是从 Whisper 对齐来的） |

## 两个坑

**1. `SaveAudioAdvanced` 和 `SongSaveMatchingLRC` 的文件名前缀必须逐字节一致**，
包括子目录和空格。不一致时后者会报 `FileNotFoundError: No saved FLAC, MP3, or Opus
found for filename prefix 'X'`——它是拿正则 `^<前缀>_(\d{5})\.(flac|mp3|opus)$`
去扫输出目录的。用一个 `SongFilename` 同时喂两个节点就不会错。

**2. 标题只能是 ASCII。** 中文标题经过命令行传参会变成乱码，
落盘的文件名跟着一起烂。

## `mode=melody` 的实测

节点说明写 `melody` 是"只生成旋律，推荐用于 cover"。实测在这首歌上：

- `melody` 43.8% vs `full` —— **没有改善**
- `abc=""` 时 `full` 和 `melody` 产出**逐字节相同**，也就是说这个参数在空谱面下不起作用

## 许可

工作流 JSON 里不含任何模型权重，只有节点连线和参数。模型本身按 YuE 自己的许可。
