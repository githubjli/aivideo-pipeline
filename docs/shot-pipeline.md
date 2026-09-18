# 镜头流水线（shot pipeline）使用说明

一个镜头 = 一个 JSON 说明书。`tools/pipeline/shot.py` 读它，依次完成：台词配音 → 时间轴 → Blender 人偶渲染（动作按台词时间对齐）→ 生成 Wan2GP 设置 → 生成视频 → 归档。

```powershell
ComfyUI_windows_portable\python_embeded\python.exe -X utf8 tools\pipeline\shot.py productions\math\shots\demo-dialogue.json
```

加 `--dry-run` 只做到"写出设置文件"，不占 GPU；用于检查时间轴和构图。

## 说明书字段

| 字段 | 含义 | 默认 |
| --- | --- | --- |
| name | 镜头名，输出到 productions/math/shots/<name>/ | 必填 |
| shot | close / medium / wide / full | medium |
| fps | 帧率；有对话时用 25（Multitalk 训练帧率） | 24 或 25 |
| frames | 无对话时的帧数（4n+1） | 49 |
| seed / resolution | 随机种子 / 生成分辨率 | 42 / 832x480 |
| colored | 上色渲染 + 保色控制（UV）而不是线稿（EV） | false |
| control | 控制字母，覆盖自动选择：E 线稿、S 形状、D 深度、P 姿态、U 原样，V 有控制视频，I 参考图 | EVI 或 UVI |
| prompt | 场景与动作描述；角色描述由 figures[].describe 自动拼接 | 必填 |
| figures[] | name（mom/kid 决定身高）、action（idle/wave/point/jump/turn）、at（动作秒区间，可省略）、ref（参考图）、describe、voice（配音样音） | 必填 |
| dialogue[] | speaker、text，可选 audio（已有配音则不再合成） | 可省略 |

规则：

- 有对话时，帧数由全部台词总长决定并向上取到 4n+1；每位说话人的动作若未指定 `at`，自动对齐到他自己的台词区间，其余时间为待机小幅摆动。这就是"语音、动作对齐"的机制：先定音频时间轴，再让动作跟时间轴。
- 两位说话人的台词按顺序合成两条音轨（CAB 模式），说话人位置按 figures 顺序：第一个在剪角处（画面右侧 55:100），第二个在其左侧（0:45）。
- 第一个 figure 站在剪角旁，第二个在它左侧 1.1 单位。
- 模型：有对话用 vace_multitalk_14B（FusioniX + VACE + Multitalk），无对话用 vace_14B_fusionix。

## 输出目录

```text
productions/math/shots/<name>/
  plan.json        帧数、帧率、时间轴、动作窗口、控制方式
  line*.wav        每句台词音频；track-*.wav 每位说话人的合并音轨
  preview/ depth/  Blender 逐帧输出；preview.mp4 送入模型的控制视频；scene.blend 可重开
  settings.json    交给 Wan2GP 的完整设置，可直接用 run-avatar-test.ps1 重跑
  result/          生成的 mp4 和抽帧条
```

## 首次端到端结果（2026-09-18 17:12，demo-dialogue）

- 时间轴：妈妈台词 0–4.38 秒，孩子台词 4.38–7.88 秒；自动得出 205 帧、25fps；动作窗口 mom:point@1-110、kid:jump@110-197。
- 总耗时 667 秒（含 Blender 渲染、音轨合并、三滑窗生成）。输出 201 帧 8.04 秒，音轨 8 秒。
- 抽帧：妈妈说话段落指向手势与张口同时出现，孩子段落跳起并张口；两人身份稳定，妈妈这次保持白色长裤（describe 里明确写了 white trousers，说明服装描述文字与参考图同样重要）。
- 说明书、计划、设置和结果都在 productions/math/shots/demo-dialogue/，`settings.json` 可脱离框架直接重跑。

## 已知边界

- 人偶是几何占位，脸和手由参考图 + 模型补；人物在画面中要占一半以上高度，否则参考图绑不上。
- 参考图要包含完整服装（全身），否则下装会漂色。
- 构图跟随只有一半，模型偏好中景；近景另用口型模型，远景不放角色。
- 保色控制（UV）在 denoising_strength=1 时只是复制输入视频；要"保留颜色但换风格"需降低 denoising_strength（实验见 docs/blender-linework-pipeline.md）。
- Mixamo 骨骼角色到位后，把 figures 的渲染后端换成 render-rigged-shot.py 即可，说明书格式不变。
