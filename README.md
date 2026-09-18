# 本地图片与视频生成

## 启动和停止

1. 双击项目根目录的 `start-comfyui.bat`。
2. 等待初始化后，用浏览器打开 http://127.0.0.1:8188 。
3. 左侧打开「工作流」，选择下面的项目工作流。
4. 用完双击 `stop-comfyui.bat`，释放本项目的 GPU 和内存占用。

启动脚本在后台运行服务，关闭浏览器不会停止服务。日志在 `logs/`，生成结果在 `outputs/`。本项目只开放本机访问，不需要登录云端账号。

## 工作流

| 工作流 | 用途 | 初始参数 |
| --- | --- | --- |
| `01-sdxl-image` | 文字生成图片 | 1024×1024、25 步、种子 42 |
| `02-wan-text-to-video` | 文字生成视频 | 1280×704、49 帧、24fps、20 步、种子 42 |
| `03-wan-image-to-video` | 图片生成视频 | 同上，输入为 `sdxl-reference.png` |
| `04b-wan-fun-control-canny` | Blender 场景线稿控制生成视频（几何精确） | 输入 `fence-v001-preview.mp4`，1280×704、49 帧、20 步、种子 42 |
| `04-wan-fun-control-depth` / `04c` | 同上但用深度图控制 | 实测对该模型几乎无效，仅留作对照 |

Blender 场景由 `tools/blender/render-depth-sequence.py` 无头生成（围栏尺寸、剪角大小、帧数、分辨率可传参），输出预览与深度序列，再用 ffmpeg 编成控制视频放到 `ComfyUI/input/`。

修改正向提示词后点击「运行」。图生视频可在 Load Image 节点选择自己的图片；当前宽高会裁切缩放输入，处理不同宽高比时请相应调整。视频默认约 2.04 秒，不含音频。

`workflows/*.json` 是可拖入 ComfyUI 的界面工作流；带 `.api.json` 后缀的文件用于脚本调用。工作流也已放入 ComfyUI 用户工作流目录。

## 当前验证状态

已完成安装和实测：SDXL 1024×1024 图片约 9–10 秒；Wan 文生视频和图生视频各约 70 秒，输出 1280×704、约 2 秒的 MP4。所有模型已完成 SHA256 校验。详细参数、测试范围和后续变更见 [DEPLOYMENT.md](DEPLOYMENT.md)。

## 复现命令

在项目目录的 PowerShell 中执行：

```powershell
.\ComfyUI_windows_portable\python_embeded\python.exe -X utf8 -s run-workflow.py 01-sdxl-image
.\ComfyUI_windows_portable\python_embeded\python.exe -X utf8 -s run-workflow.py 02-wan-text-to-video
.\ComfyUI_windows_portable\python_embeded\python.exe -X utf8 -s run-workflow.py 03-wan-image-to-video
```

请逐条运行，避免多任务争用显存。每次调用的任务 ID、结果、耗时和完整执行历史保存在 `logs/`。

## 口型与音频（Wan2GP 独立运行器）

与 ComfyUI 完全分离，程序在 `tools/avatar/Wan2GP`，权重在其 `ckpts` 与 `loras` 目录。已验证：InfiniteTalk、Hunyuan Avatar、LongCat Avatar 1.5 三套口型模型，以及 Index TTS 2（声线克隆）、Stable Audio 3 Small（无人声垫乐）、ACE-Step 1.5（歌曲）、MMAudio（按画面配环境音）。

1. 双击 `start-avatar.bat`，等待后打开 http://127.0.0.1:7861 ，在界面顶部选择模型。
2. 不要同时运行 ComfyUI 生成任务；14B 口型模型加载后整卡显存在 8 到 15 GB 之间。
3. 无界面批量方式：在项目目录 PowerShell 执行下面命令，结果在 `productions/math/tests/avatar/out/`，耗时、显存和日志在 `logs/avatar-test-*`。

```powershell
powershell -ExecutionPolicy Bypass -File tools/avatar/run-avatar-test.ps1 -Settings productions/math/tests/avatar/infinitetalk-mom-test.json -Attention sage2
```

测试配置模板（口型三套、配音、垫乐、歌曲、环境音各一份）都在 `productions/math/tests/avatar/`，改台词、参考图和音频路径即可复用。各模型实测参数、对比结果、许可注意事项见 [tools/avatar/DEPLOYMENT.md](tools/avatar/DEPLOYMENT.md)。

## 版本控制

仓库：https://github.com/githubjli/aivideo-pipeline （分支 main，基线标签 comfyui-v1）。只提交脚本、工作流、清单和文档；程序、模型、下载、日志、输出和生成的音视频都在 .gitignore 里，按 [baselines/comfyui-v1/BASELINE.md](baselines/comfyui-v1/BASELINE.md) 重建。market 目录的分析文档只留本地。

日常提交在项目目录终端执行 `git add -A`、`git commit -m "..."`、`git push`；Git for Windows 已安装并通过浏览器登录，不需要再输凭据。

## 文件与维护

- 主程序和模型：`ComfyUI_windows_portable/ComfyUI/`
- 独立 Python：`ComfyUI_windows_portable/python_embeded/`
- 输入图片：`ComfyUI_windows_portable/ComfyUI/input/`
- 输出：`outputs/sdxl/` 与 `outputs/wan/`
- 模型校验记录：`logs/model-verification.json`
- 原始安装包、模型来源信息与许可证：`downloads/`
- 详细版本、排错和后续变更：`DEPLOYMENT.md`

使用项目根目录的启动入口才能统一输出路径；官方原始启动脚本使用其自己的默认设置。首次稳定运行后，不要为普通生成任务随意升级依赖。升级或安装节点前记录版本，保留已验证工作流。

SDXL 使用 CreativeML Open RAIL++-M，许可证已保存为 `downloads/SDXL-LICENSE.md`；Wan 重打包仓库标注 Apache-2.0，说明保存在 `downloads/WAN-README.md`。具体使用条件以对应许可证为准。
