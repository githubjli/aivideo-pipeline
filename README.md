# aivideo-pipeline

本地生成儿童数学讲解视频的流水线：ComfyUI 出图和基础视频，Blender 出几何与动作，Wan2GP 出口型、角色一致性视频和全部音频。一台 RTX 4090 D（24 GB）即可运行。仓库只放脚本、工作流、清单和文档；程序与模型按文档重建。

## 快速开始

**1. 跑一条镜头（推荐入口）**

```powershell
ComfyUI_windows_portable\python_embeded\python.exe -X utf8 tools\pipeline\shot.py productions\math\shots\demo-dialogue.json
```

复制 `productions/math/shots/demo-dialogue.json` 改台词、动作、提示词即可生成新镜头；字段说明见 [docs/shot-pipeline.md](docs/shot-pipeline.md)。加 `--dry-run` 只渲染 Blender 和写设置，不占 GPU。

**2. 口型与音频的网页界面**：双击 `start-avatar.bat`，打开 http://127.0.0.1:7861 ，顶部选模型。

**3. ComfyUI 图片与基础视频**：双击 `start-comfyui.bat`，打开 http://127.0.0.1:8188 ，左侧"工作流"里选项目工作流；用完双击 `stop-comfyui.bat`。

同一时刻只运行一个 GPU 生成任务；14B 模型加载后显存 8 到 15 GB，ComfyUI 生成时接近 24 GB。

## 已验证的能力

| 能力 | 工具 | 一条的耗时 |
| --- | --- | --- |
| 文生图 | ComfyUI + SDXL（工作流 01） | 约 10 秒 |
| 文生 / 图生视频 | ComfyUI + Wan 2.2 TI2V-5B（02、03） | 约 70 秒 |
| Blender 线稿控制的场景视频 | ComfyUI + Wan2.2 Fun Control 5B（04b） | 约 67 秒 |
| 角色身份 + 位置 + 动作 | Wan2GP VACE FusioniX + 参考图 | 约 130 秒 |
| 同镜头双人对话 | Wan2GP VACE + Multitalk | 8 秒约 10 分钟 |
| 口型特写 | InfiniteTalk / Hunyuan Avatar / LongCat 1.5 | 2 / 14 / 3 分钟 |
| 配音、垫乐、歌曲、音效 | Index TTS 2 / Stable Audio 3 / ACE-Step 1.5 / MMAudio | 1 到 3 分钟 |

全部实测数字、对照实验和边界见 [docs/phase-1-summary.md](docs/phase-1-summary.md)；文档阅读顺序见 [docs/README.md](docs/README.md)。

## 目录

```text
docs/                    文档（地图、阶段总结、流水线说明、实验记录）
tools/pipeline/          镜头流水线 shot.py
tools/blender/           Blender 无头脚本：场景、人偶、骨骼角色、姿态导出
tools/avatar/            Wan2GP 运行器脚本、模型清单、测试运行器、部署记录
workflows/               ComfyUI 工作流（UI 版与 API 版）
baselines/comfyui-v1/    冻结的 ComfyUI 初始版本
productions/math/        角色设定、镜头说明书与产物（产物不入 git）
ComfyUI_windows_portable/ tools/blender/blender-*/ tools/avatar/Wan2GP/   程序本体，不入 git
downloads/ logs/ outputs/   安装包、日志、输出，不入 git
```

## 环境重建

1. ComfyUI：按 [baselines/comfyui-v1/BASELINE.md](baselines/comfyui-v1/BASELINE.md) 解压便携包、校验模型、运行 `prepare-workflows.py`。
2. Wan2GP：按 [tools/avatar/DEPLOYMENT.md](tools/avatar/DEPLOYMENT.md) 建虚拟环境，运行 `tools/avatar/download-models.py --download` 按清单下载并校验全部权重。
3. Blender：从 blender.org 下载 4.2.23 便携版解压到 `tools/blender/`，校验值见 [DEPLOYMENT.md](DEPLOYMENT.md)。

## 版本控制

仓库 https://github.com/githubjli/aivideo-pipeline ，分支 main，基线标签 comfyui-v1。日常在项目目录执行 `git add -A`、`git commit -m "..."`、`git push`。market 目录的分析文档只留本地。

## 许可提示

SDXL（CreativeML Open RAIL++-M）、Wan 系列（Apache-2.0）、ACE-Step（MIT）可商用；Index TTS 2 与 Stable Audio Open 有条款门槛，MMAudio 官方权重为 CC BY-NC，Mixamo 资产不可再分发。商用前逐个核对。
