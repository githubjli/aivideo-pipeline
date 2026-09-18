# Blender 线稿驱动视频：实现记录

日期：2026-09-17 建立，2026-09-18 补充 3D 人物实验。基线冻结见 `baselines/comfyui-v1/BASELINE.md`。

## 一句话

Blender 逐帧渲染平光几何 → ffmpeg 编成视频 → ComfyUI Canny 提取线稿 → Wan2.2 Fun Control 5B 以线稿为结构条件、以提示词为外观条件一次性生成整段视频。几何、尺寸、相机运动由 Blender 决定；颜色、材质、光照、风格由视频模型决定。

## 组件与版本

| 层 | 组件 | 版本 / 来源 |
| --- | --- | --- |
| 3D | Blender LTS 便携版 | 4.2.23，download.blender.org，SHA256 `82e79147…d910cb`，目录 tools/blender/blender-4.2.23-windows-x64 |
| 场景脚本 | tools/blender/render-depth-sequence.py | 参数：--out --frames --width --height --fps --cut --near --far --figure |
| 转码 | ffmpeg 9.0.1 | tools/avatar/Wan2GP/ffmpeg_bins（Wan2GP 自动下载） |
| 编排 | ComfyUI 0.36.0 核心节点 | LoadVideo、GetVideoComponents、Canny、Wan22FunControlToVideo、UNETLoader、CLIPLoader、VAELoader、ModelSamplingSD3、KSampler、VAEDecode、CreateVideo、SaveVideo；无第三方节点 |
| 模型 | wan2.2_fun_control_5B_bf16 | Comfy-Org 重打包 @ c4f60d30，SHA256 ace4718a…，10.00 GB |
| 模型 | umt5_xxl_fp8_e4m3fn_scaled、wan2.2_vae | 与 TI2V-5B 基线共用 |
| 项目脚本 | prepare-workflows.py、run-workflow.py、verify-models.py | 模板派生、API 提交与记录、SHA256 校验 |

## 步骤（可复现）

```powershell
# 1. Blender 渲染 49 帧 1280x704 预览与深度（约 26 秒）
tools\blender\blender-4.2.23-windows-x64\blender.exe -b --python tools\blender\render-depth-sequence.py -- --out productions\math\tests\depth\fence-v001 --frames 49 --width 1280 --height 704 --fps 24
```

```powershell
# 2. 预览序列编成控制视频，放入 ComfyUI 输入目录
tools\avatar\Wan2GP\ffmpeg_bins\ffmpeg.exe -y -framerate 24 -i productions\math\tests\depth\fence-v001\preview\preview_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 10 ComfyUI_windows_portable\ComfyUI\input\fence-v001-preview.mp4
```

```powershell
# 3. 生成工作流（从官方模板 video_wan2_2_5B_fun_control 派生）并提交
ComfyUI_windows_portable\python_embeded\python.exe -X utf8 -s prepare-workflows.py
ComfyUI_windows_portable\python_embeded\python.exe -X utf8 -s run-workflow.py 04b-wan-fun-control-canny
```

关键参数：Canny 阈值 0.1 / 0.4；Wan22FunControlToVideo 1280×704×49；KSampler 种子 42、20 步、cfg 5、uni_pc/simple；ModelSamplingSD3 shift 8；输出 24fps H.264。

## 结果

| 试验 | 控制信号 | 耗时 | 峰值整卡显存 | 几何跟随 |
| --- | --- | --- | --- | --- |
| 04 | 深度图 8–28 | 67.4 秒 | 21689 MiB | 弱 |
| 04c | 深度图 10–22 | 64.3 秒 | 约同上 | 与 04 逐帧相同，深度无效 |
| 04b | 平光预览 → Canny | 67.3 秒 | 约同上 | 好：闭合围栏、斜切角、柱子、70° 环绕全部对应 |

抽帧对照：productions/math/tests/depth/fence-v001/result/。输出视频：outputs/wan/fun_control_*_00001_.mp4。

## 原理要点

- Wan22FunControlToVideo 把控制视频经 VAE 编码后与噪声潜变量按通道拼接，模型训练时学过"视频 + 其 Canny 边缘"的配对，因此结构会对齐线稿。
- 生成是整段联合去噪（49 帧压成 13 个潜帧，时空注意力跨帧），流畅与颜色一致性来自联合生成，不来自 Blender。
- 同种子 A/B 对照可判断某条件是否生效：输出逐帧相同即无效。

## 已知边界

- 单个物体的颜色材质、角色身份不受线稿控制，只能靠提示词、参考图或 LoRA。
- 没有线条的区域（天空、远景）由模型自由补，换种子会变。
- 单次长度受显存限制（本机 5B 约 49–81 帧），更长镜头需滑窗拼接。
- 太细的杆件在画面上小于 2–3 像素会丢线。

## 3D 人物实验（2026-09-18）

脚本加 `--figure`：在剪角旁放一个由球体和圆柱拼成的简易人偶（头、躯干、双腿、双臂），整段转身 60°，右臂挥手。渲染 → 平光预览 → Canny → Fun Control，两条：

| 工作流 | 条件 | 耗时 | 结果 |
| --- | --- | --- | --- |
| 04d-wan-fun-control-figure | 线稿 + 提示词描述"短发、圆眼镜、青色衬衫的妈妈" | 76.5 秒 | 人偶位置、转身、挥手全部跟随；模型把人偶画成一个穿青色衬衫、戴眼镜的卡通人，风格与围栏场景一致，但只是"符合描述的某个人"，不是角色表里的妈妈 |
| 04e-wan-fun-control-figure-ref | 同上 + ref_image = mom-ref-front.png | 73.4 秒 | 人物发型、衬衫颜色更接近参考图；但参考图的白底同时把整个场景带成了米白背景，卡通草地风格被削弱 |

结论：

1. **可用**：3D 人偶能精确控制人物在画面里的位置、朝向、姿态和动作时序，这是提示词做不到的；线稿和围栏几何一起被遵守。
2. **身份靠不住**：5B Fun Control 的 ref_image 是全局外观参考，既影响人也影响背景；角色脸和细节仍是模型自由发挥。要锁定"数学妈妈"，必须换带参考主体能力的模型或训练角色 LoRA（见下节）。
3. **人偶太小时脸部无线条**，模型只能猜；正式镜头里人物应占画面更大比例，或者用带五官轮廓的模型（Mixamo/Rigify 角色）而不是圆柱人偶。
4. 素材归档：`productions/math/tests/depth/<镜头>/{scene.blend, preview/, depth/, control/, result/}`，control/ 是送进 ComfyUI 的视频副本，result/ 是生成结果与抽帧条。

## 角色一致性：VACE FusioniX 实验结果（2026-09-18）

| 镜头 | 控制 | 结果 |
| --- | --- | --- |
| 全景 fence-v002-figure，人偶很小 | EVI（Canny + 参考图） | 身份很准，但人物被放大到远超人偶轮廓 |
| 同上 | SVI（Shapes + 参考图） | 几何严格，人偶被画成路人，妈妈在末尾另处冒出 |
| **中景 fence-v003-figure-medium，人偶占画面约三分之二** | **EVI（Canny + 参考图）** | **身份、位置、转身挥手、围栏几何全部对上，无闪烁，136 秒，峰值显存 9.4 GB** |

结论与规则：

1. 角色镜头走 VACE FusioniX：`video_prompt_type` 用 `EVI`，`image_refs` 放角色正面头肩图，`remove_background_images_ref=1`，10 步、guidance 1、flow_shift 2。
2. 人偶在画面里要足够大（高度不小于画面一半），否则参考主体无法绑定到人偶轮廓。
3. 场景全景不放角色时，用 Fun Control 5B 的 Canny 或 VACE 的 Shapes 模式只控几何。
4. 提示词要把参考角色和动作写明（"the referenced mother character ... turns and waves"），并描述参考图之外的背景。
5. 复现命令：Blender 加 `--figure --focus-figure` 渲染；`run-avatar-test.ps1 -Settings productions/math/tests/avatar/vace-fusionix-medium-canny.json -Attention sage2`。

## 稳定性测试序列（2026-09-18 15:00–15:20，人偶 + VACE FusioniX EVI + 参考图，种子 42）

人偶改为 `mathscene.add_mannequin`：肩、髋各有枢轴，脚、手为独立部件，头身比可调（默认 6），动作 idle / wave / point / jump / turn；`render-mannequin-shot.py` 支持 1–2 个人物与 close / medium / wide / full 四种相机。

| 步骤 | 场景 | 结果 | 耗时 / 显存 |
| --- | --- | --- | --- |
| 1 单角色三景别 | s1-mom-close / medium / wide | 三个镜头身份一致（发型、眼镜、衬衫、腰包、白裤）。构图只跟随一半：近景被拉成半身、远景被拉成中景，模型偏好中景构图 | 各约 130 秒 / 9.2 GB |
| 2 双人 | s2-duo-medium，mom:wave + kid:idle，image_refs = [妈妈, 孩子] | 两人都出现且左右位置正确，孩子的黄色背带裤、乱发、蓝鞋准确；妈妈上身准确但裤子漂成牛仔裤 | 134 秒 / 9.3 GB |
| 3 双动作 | s3-duo-actions，mom:point + kid:jump | 妈妈右臂指向、孩子跳起双臂上举都被执行；身份同上 | 135 秒 / 8.9 GB |

| 4 对话 | s4-duo-dialogue，模型 vace_multitalk_14B（FusioniX 底模 + VACE 模块 + Multitalk 模块 2.39 GiB），audio_prompt_type=CAB（两段配音顺序播放），speakers_locations="55:100 0:45"（说话人 1 妈妈在右、说话人 2 孩子在左），配音：妈妈 mom-test-zh.wav 4.38 秒 + 孩子 Index TTS 2 新生成 3.49 秒，201 帧 25fps 三个 81 帧滑窗 | 两人面对面，妈妈段落妈妈张口、孩子段落孩子张口，音轨 8 秒完整；身份稳定，妈妈裤子仍漂色 | 578 秒 / 10.1 GB |

结论：参考图绑定在双人场景可用，绑定顺序与画面左右无关、按提示词描述和人偶体型匹配；对话可以在同一镜头内完成，不必拆成两个口型特写；近景/远景需要另想办法（近景可改用口型模型，远景接受"中景化"或改用无角色的几何控制）。妈妈裤子漂色说明参考图应包含完整服装（当前裁剪只到大腿），下一版参考图改为全身。口型是否与中文音节精确对齐、两人轮流说话时另一人是否保持闭嘴，需人工看片。

## 颜色能否从 Blender 带过去（2026-09-18 16:50）

问题："模型贴图能否替换"。实验：`render-mannequin-shot.py --colored` 给地面、围栏、两个人偶赋平面色（青衬衫、白裤、黄背带裤、蓝鞋），同一双动作场景跑三种控制：

| 控制 | denoising_strength | 结果 |
| --- | --- | --- |
| UVI（原样 + 参考图） | 1.0 | 输出几乎等于输入的上色渲染，人偶、灰天空原样保留，没有任何卡通化 |
| UVI | 0.6 | 与上一条无差别，该参数对 VACE 原样模式不起作用 |
| EVI（线稿 + 参考图） | 1.0 | 与未上色版本一致：颜色信息在边缘提取时全部丢失，妈妈裤子仍漂成牛仔裤 |

结论：VACE 的"原样"模式是复制而不是重绘，不能作为"保留颜色、替换风格"的通道；Blender 里的材质和贴图对现在这条线稿链路没有意义。要控制服装和物体颜色，可靠的手段只有两个：参考图（角色用全身参考图，道具也可以作为 People / Objects 参考图给一张）和提示词。真正的"贴图替换"要等有了带蒙皮的角色后，用 VACE 的遮罩局部重绘（Masked Area）单独改某一件衣服，这条还没验证。

## 路线 A：Mixamo 骨骼角色（2026-09-18 脚本就绪，等待资产）

- 资产接收目录与下载清单：`productions/math/shared/characters/duo/rig/README.md`（角色 FBX 带蒙皮 T-pose；动作 FBX 不带蒙皮、30fps）。FBX 不入库。
- `tools/blender/mathscene.py`：围栏、灯光（主光 + 补光，避免纯黑剪影）、相机环绕、深度合成器、以及从骨架导出 OpenPose 18 点关节的函数；支持 Mixamo（mixamorig:* 命名）与 Rigify 元骨架两种骨骼命名。
- `tools/blender/render-rigged-shot.py`：导入角色 FBX 并按 `--height-m` 缩放到 1.65 单位，导入动作 FBX 把动作挂到角色骨架上（30fps 自动重映射到 24fps），放到剪角旁，`--shot medium|full` 选相机，输出 preview/、depth/、pose/joints.json 和 scene.blend。`--selftest-metarig` 用 Blender 自带 Rigify 元骨架加脚本化的转身挥手代替 FBX，用于在没有 Mixamo 文件时验证流程。
- `tools/blender/draw-openpose.py`：把 joints.json 画成 ControlNet 配色的 OpenPose 序列（黑底、肢体椭圆、关节圆点），用 ComfyUI 自带 Python 运行。
- 自测（selftest-metarig，25 帧中景）：渲染 + 导出 + 绘制全部通过，骨架比例和配色正确；发现默认朝向让人物侧对相机，已把 `--facing` 默认改为 0（Mixamo 与 Rigify 导入后都面向 -Y）。元骨架没有网格，预览里只有围栏，这是预期。
- 下一步：Mixamo 文件到位后跑 `render-rigged-shot.py`，预览走线稿（EV）、骨架走姿态原始格式（V + P 组合，PSV），参考图仍用 mom-ref-front.png，与圆柱人偶版对照。

## 跨段、跨镜头一致性的候选模型

| 候选 | 所在环境 | 能力 | 代价 | 建议 |
| --- | --- | --- | --- | --- |
| Wan2.1 VACE 14B INT8（Wan2GP 内置 vace_14B） | 已装的 Wan2GP | 参考图 + 控制视频（线稿/深度/姿态）同时输入，专为"参考主体 + 结构控制"设计 | 约 17 GB 权重，sage2 下与 InfiniteTalk 同量级 | 第一优先：不加环境，直接验证"参考图锁角色 + Blender 线稿锁几何" |
| Wan2.2 Fun VACE 14B fp8（Comfy-Org 重打包） | ComfyUI | 同上，Wan2.2 双专家版 | 两个 16.15 GB 文件，24 GB 显存需分块加载 | 若坚持 ComfyUI 单环境再下 |
| StandIn / Lynx（Wan2GP 内置） | Wan2GP | 单张人脸参考保持身份 | 附加模块几 GB | 真人脸效果好，卡通角色待验证 |
| 角色 LoRA（SDXL 用 kohya；Wan 用 musubi-tuner） | 需新增训练环境 | 最稳的身份锁定，可跨模型复用 | 需 20–50 张一致的角色图与数小时训练 | 参考图路线不够时再上 |
