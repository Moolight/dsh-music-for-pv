# vendor/

第三方代码放这里。目前只有一个文件。

## `tuikit.py`

TUI 风格 PV 的绘图工具箱：画字、画框、配色、立绘的半调/字符网格化，
以及后期（辉光、残影、扫描线、暗角）。

- **出处**：[world-execute-me-dsh-pv](https://github.com/MisakaZentai/world-execute-me-dsh-pv)
  的 `film/tui_pv_world_execute_20260926/tuikit.py`
- **作者**：MisakaZentai
- **许可**：MIT（`LICENSE` 全文见仓库根的 [LICENSE](../../LICENSE) 说明）
- **本项目的改动**：**只有一处**，见文件里标了 `--- local change ---` 的那几行。
  上游把字体和立绘的路径写死在自己仓库里（`Path(__file__).parents[1]/...`），
  所以在别处跑不起来；这里改成指向本仓库的 `assets/`，并保留环境变量覆盖
  （`PV_ASSETS` / `PV_SPRITES`）。其余一字未动。

**要改工具箱本身的话**，别改这个副本——去上游改，然后用 `PV_TUI`
指向上游克隆，`pvlib/kit.py` 会优先用那个：

```bash
export PV_TUI=/path/to/world-execute-me-dsh-pv/film/tui_pv_world_execute_20260926
```

## 为什么把代码 vendor 进来

为了让这个仓库**克隆下来就能跑**，不需要先去 clone 另一个仓库、再设一个环境变量。
代价是上游更新不会自动同步过来——但这套工具的接口很稳定，而且比"跑不起来"便宜。
