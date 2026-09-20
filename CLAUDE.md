# CLAUDE.md — 给下一次会话的项目说明

这是"数学妈妈"儿童数学视频的本地生成流水线。读完本文再看 docs/README.md（文档地图）和 docs/phase-1-summary.md（第一阶段总结），不要重做已经验证过的事。

## 一句话现状（2026-09-20）

ComfyUI（图片、基础视频、Blender 线稿控制）、Wan2GP（口型三套、音频四件套、VACE 角色一致性、VACE+Multitalk 对话）、Blender 4.2.23 全部装好并出片；130 个权重 120.33 GiB 全部 SHA256 校验通过；镜头流水线 tools/pipeline/shot.py 可一键从说明书生成带配音、动作、口型的镜头。仓库 https://github.com/githubjli/aivideo-pipeline ，main 分支与本地一致。

## 怎么跑（都在项目根目录）

- 镜头：`ComfyUI_windows_portable\python_embeded\python.exe -X utf8 tools\pipeline\shot.py productions\math\shots\<name>.json`（`--dry-run` 不占 GPU）。
- 单个 Wan2GP 设置文件：`powershell -File tools\avatar\run-avatar-test.ps1 -Settings <json> -Attention sage2`；多个顺序跑用 tools\avatar\run-test-queue.ps1（逗号连接）。
- ComfyUI 工作流：`start-comfyui.bat` 后 `python -X utf8 -s run-workflow.py 04b-wan-fun-control-canny`；用完 `stop-comfyui.bat`。
- Wan2GP 网页：`start-avatar.bat` → http://127.0.0.1:7861 。ComfyUI 网页 http://127.0.0.1:8188 。
- Blender 无头：`tools\blender\blender-4.2.23-windows-x64\blender.exe -b --python tools\blender\render-mannequin-shot.py -- --out <dir> --shot medium --figures mom:point,kid:jump`。
- 权重清单与下载：`tools\avatar\download-models.py`（`--download`，`--only 目录…`）；ComfyUI 侧 `verify-models.py`。
- git：系统 Git for Windows 已装，凭据走浏览器登录；在我的 PowerShell 里需先把 `C:\Program Files\Git\cmd` 加进 PATH。提交信息末尾加 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`。

## 硬规则

- 同一时刻只跑一个 GPU 生成任务；跑 Wan2GP 前确认 ComfyUI 已停（它会把模型留在显存里）。
- 不装第三方 ComfyUI 节点；不升级两套环境的依赖；改动前看 baselines/comfyui-v1/BASELINE.md。
- 每个验证结果都写进对应文档，附配置、耗时、峰值显存；主观项标"待人工验收"；失败也记录。
- 生成产物、模型、日志不入 git；market/ 目录只留本地。

## 已踩过的坑（别再踩）

- PowerShell 5.1 里对原生程序用 `2>&1` 且 ErrorActionPreference=Stop，会把 tqdm 进度条当成终止错误并杀掉 Python。用 Start-Process 重定向到文件。
- Wan2GP 运行中改 wgp_config.json 会被覆盖，先停服务再改。
- Hugging Face 直连大文件停滞：用 download-models.py 的分块续传，或 ComfyUI 侧走 hf-mirror。
- Wan2GP 首次加载任何模型会检查一组共享资产，清单里已包含；LongCat 的 dmd_lora 必须在 loras/longcat_avatar_v1_5/。
- Fun Control 5B 对深度图无效，只认线稿；VACE "原样"模式是复制不是重绘。
- 人偶在画面里不足一半高度时参考图绑不上；参考图裁到大腿会让下装漂色。
- 用 -File 启动的 PowerShell 脚本，数组参数要用逗号连成一个字符串。

## 待办（按优先级）

1. 用户看片验收：口型模型选主力（候选 InfiniteTalk）、对话镜头非说话者是否闭嘴、音色。
2. Mixamo 资产：productions/math/shared/characters/duo/rig/ 目前为空（用户说放了但没找到）；到位后跑 tools/blender/render-rigged-shot.py，并把姿态骨架（P 模式）接进 VACE。
3. 真人样音固定妈妈、孩子声线（Index TTS 2）。
4. 全身参考图替换现有头肩图（characters-v001.png 里裁）。
5. 把口型特写接进 shot.py（近景自动切换口型模型）。
6. 许可复核：Index TTS 2、Stable Audio Open 条款门槛；MMAudio 权重非商用。
