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

## 跨段、跨镜头一致性的候选模型

| 候选 | 所在环境 | 能力 | 代价 | 建议 |
| --- | --- | --- | --- | --- |
| Wan2.1 VACE 14B INT8（Wan2GP 内置 vace_14B） | 已装的 Wan2GP | 参考图 + 控制视频（线稿/深度/姿态）同时输入，专为"参考主体 + 结构控制"设计 | 约 17 GB 权重，sage2 下与 InfiniteTalk 同量级 | 第一优先：不加环境，直接验证"参考图锁角色 + Blender 线稿锁几何" |
| Wan2.2 Fun VACE 14B fp8（Comfy-Org 重打包） | ComfyUI | 同上，Wan2.2 双专家版 | 两个 16.15 GB 文件，24 GB 显存需分块加载 | 若坚持 ComfyUI 单环境再下 |
| StandIn / Lynx（Wan2GP 内置） | Wan2GP | 单张人脸参考保持身份 | 附加模块几 GB | 真人脸效果好，卡通角色待验证 |
| 角色 LoRA（SDXL 用 kohya；Wan 用 musubi-tuner） | 需新增训练环境 | 最稳的身份锁定，可跨模型复用 | 需 20–50 张一致的角色图与数小时训练 | 参考图路线不够时再上 |
