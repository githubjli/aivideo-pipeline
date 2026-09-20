# 口型与音频运行器（Wan2GP）部署与实验记录

状态（2026-09-20 整理）：**三套口型模型、音频四件套、VACE FusioniX 角色一致性、VACE + Multitalk 对话全部跑通并有样片；130 个权重文件 120.33 GiB 全部 SHA256 校验通过。** 主观质量（口型对齐、音色、表情）待人工验收。本文按主题重排，各节保留原始时间戳；阅读顺序与全项目文档地图见 docs/README.md。

## 架构决策

Windows 未安装 WSL；采用官方 Hunyuan 页面链接的社区低显存运行器 Wan2GP，代码来自 https://github.com/deepbeepmeep/Wan2GP 。已核对当前源码包含 InfiniteTalk、Hunyuan Avatar、LongCat Avatar 1.5 三种架构及 INT8 权重定义。

同一隔离运行器支持三种模型，避免安装三套相互重复的依赖；与原 ComfyUI 完全分离。权重为 DeepBeepMeep 发布的兼容量化版本，不是各研究仓库的原始全精度安装。源码提交记录在 downloads/wangp-commit.json；模型提交与 SHA256 记录在本目录 model-manifest.json。

## 状态（2026-09-16 15:10 核查）

- Python 3.11.14：已安装到本目录 python；虚拟环境在 Wan2GP/.venv。
- PyTorch 2.10.0+cu130：已安装，CUDA 识别 4090D，矩阵运算通过。
- 官方 requirements：已安装完成，快照 installed-requirements.txt（mmgp 3.8.0、gradio 5.29.0、transformers 4.54.0、diffusers 0.36.0、optimum-quanto 0.2.7）。未安装 sageattention、flash_attn、triton、xformers、llamacpp_gguf_cuda，当前只能用 sdpa 注意力；启动日志显示 GGUF CUDA 内核回退，仅影响可选的提示词增强/Deepy，不影响三套口型模型。
- 三个模型家族的处理器已通过导入验证，支持类型名确认为 infinitetalk、hunyuan_avatar、longcat_avatar_v1_5。
- Web UI：已在后台启动（14:49，进程 python.exe，日志 logs/avatar-server.log），http://127.0.0.1:7861 返回 200；启动时自动下载了 ffmpeg 9.0.1 到 Wan2GP/ffmpeg_bins。尚未在浏览器里做任何模型加载或生成。
- 模型下载：进程仍在运行（download-models.py --download，14:28 启动）。15:08 时 4 个文件已校验（3.57 GiB），分块缓存 10.71 GiB；InfiniteTalk 音频模块、三个 Wan VAE 已完成，i2v 480p 底模约 44%，umt5 文本编码器约 56%。实测吞吐约 6.5 MB/s，剩余约 59 GiB，预计还需 2.5–3 小时。
- 视频生成：三套均未验证。测试素材只有配音 productions/math/tests/avatar/mom-test-zh.wav 与角色参考图 productions/math/shared/characters/duo/v001/characters-v001.png。

## 15:30 起的处理记录

- 清单扩展：download-models.py 的 assets() 追加 Wan2GP 共享资产 8 个目录（20 个新文件，det_align 已有）和 InfiniteTalk 模板用的 4 步加速 LoRA（loras_accelerators/Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors，0.69 GiB）。清单现为 71 文件、78.03 GiB，全部锁定在原有仓库提交。清单行新增可选 target 字段：LoRA 直接落到 Wan2GP/loras/wan_i2v（源码 get_lora_dir 对 i2v 类返回 wan_i2v）。
- 脚本新增 `--only 目录…` 参数，可只下载指定顶层目录。共享资产与 LoRA 已用该参数另起两个下载进程并行（日志 logs/avatar-shared-download.log、logs/avatar-lora-download.log），不与主进程争用同一分块目录。
- 收尾脚本 tools/avatar/finalize-download.ps1 已在后台运行（日志 logs/avatar-finalize.log）：等待所有下载进程退出后，对整份清单再跑一遍大小与 SHA256 校验并补缺，然后把 LongCat 的 dmd_lora.safetensors 硬链接到 loras/longcat_avatar_v1_5。**18:52 完成：127 个文件、100.90 GiB 全部 SHA256 校验通过，分块缓存清空，LoRA 已硬链接。** 主下载 14:28 开始，总计约 4.5 小时。
- 配置：已停服务后写入 wgp_config.json（last_model_type=infinitetalk，transformer_types 三个口型模型，deepy_enabled=0，enhancer_enabled=0），服务已重启并返回 200。旧日志改名 logs/avatar-server-1449.log。
- 测试素材：从角色总图裁出母亲正面头肩参考 productions/math/tests/avatar/mom-ref-front.png（240×320）；配音实测 4.38 秒、22050Hz 单声道。
- InfiniteTalk 无界面测试配置 productions/math/tests/avatar/infinitetalk-mom-test.json 已通过 `wgp.py --process … --dry-run` 校验：480x640、113 帧（两个 81 帧滑窗）、4 步、种子 42、加速 LoRA。运行方式与结果见「验证结果」。

## 加速：Triton + SageAttention 2（2026-09-16 16:50）

- 安装：用项目自带 uv 向 Wan2GP/.venv 安装 triton-windows 3.6.0.post26 和 sageattention 2.2.0+cu130torch2.9.0andhigher.post4（woct0rdho 提供的 Windows 轮子，Wan2GP 安装文档指定版本）。安装前快照 installed-requirements.before-sage2.txt，安装后快照已覆盖 installed-requirements.txt。
- 验证：GPU 上 1×8×4096×128 bf16 注意力，首次调用含 Triton 编译 0.9 秒；10 次调用 sage2 0.005 秒、sdpa 0.011 秒；与 sdpa 输出最大绝对差 0.0063。Wan2GP `get_attention_modes()` 已列出 sdpa、auto、sage、sage2。
- 整段对比（同一配置、同一种子 42，InfiniteTalk 113 帧）：

| 注意力 | 队列总耗时 | 第一窗 4 步 | 第二窗 4 步 | 采样峰值整卡显存 | 输出 |
| --- | --- | --- | --- | --- | --- |
| sdpa | 138 秒 | 68 秒 | 32 秒 | 未采样 | infinitetalk-mom-test(2).mp4 |
| sage2 | 130 秒 | 43 秒 | 22 秒 | 8034 MiB | infinitetalk-mom-test(4).mp4 |

  去噪部分快约 35%，总耗时差距小是因为模型加载和 VAE 解码（每窗约 37 秒）不变。抽帧对比（frames/infinitetalk-sage2-strip.png 与 infinitetalk-strip.png）画面几乎一致，无明显退化。
- 已切换：start-avatar.ps1 改为 `--attention sage2`；run-avatar-test.ps1 默认仍是 sdpa，需要时加 `-Attention sage2`。
- 顺手清理：删除 ckpts/.cache/huggingface/download 下 4 个停滞残留文件（约 1.2 GB）。

## InfiniteTalk 验证结果｜2026-09-16 16:23

首条样片已生成并可解码：`productions/math/tests/avatar/out/infinitetalk-mom-test(2).mp4`（同目录不带 (2) 的文件是第一个滑窗的中间产物，由 keep_intermediate_sliding_windows=1 产生）。

| 项目 | 实测 |
| --- | --- |
| 配置 | infinitetalk-mom-test.json：480×640、113 帧、两个 81 帧滑窗、4 步、种子 42、lightx2v 加速 LoRA、sdpa、profile 4 |
| 输出 | H.264 480×640、25fps、113 帧、4.52 秒；AAC 16kHz 单声道 4.48 秒，配音完整 |
| 耗时 | 队列总计 2 分 18 秒（含模型加载）；第一窗 4 步约 68 秒，第二窗约 32 秒，VAE 解码每窗约 37 秒 |
| 显存 | 本次未采样（见下），下次运行由 run-avatar-test.ps1 记录 |
| 命令 | `wgp.py --process <json> --output-dir <dir> --attention sdpa --profile 4`，stdout/stderr 重定向到文件 |

前两次运行在“Encoding Prompt”后进程无提示退出，原因已查明：run-avatar-test.ps1 用 `2>&1` 把 Python 的 stderr 接进 PowerShell 5.1 管道，第一条 tqdm 进度条（写在 stderr）在 ErrorActionPreference=Stop 下被当成终止错误，管道中断把 Python 一起杀掉。不是模型或 CUDA 问题。脚本已改为 Start-Process 重定向到文件后再汇总日志。

以上只证明“程序跑通、音视频完整”。抽帧初看（out/frames/infinitetalk-strip.png，每 16 帧一张）：人物身份、发型、眼镜、衣着与参考图一致，嘴部有明显开合与表情变化，有一帧闭眼属正常眨眼；嘴形是否与中文音节对齐需要人工看片后另行记录。

## Hunyuan Avatar 验证结果｜2026-09-16 17:48

输出 `productions/math/tests/avatar/out/hunyuan-avatar-mom-test.mp4`，抽帧条 out/frames/hunyuan-strip.png。

| 项目 | 实测 |
| --- | --- |
| 配置 | hunyuan-avatar-mom-test.json：预算 832×480、129 帧、30 步、guidance 7.5、种子 42、sage2、profile 4 |
| 输出 | H.264 544×736（程序按参考图比例在同像素预算内自动定尺寸）、25fps、129 帧、5.16 秒；AAC 22050Hz，配音完整 |
| 耗时 | 队列 14 分 11 秒；去噪 30 步约 13 分 24 秒（约 27 秒/步），VAE 解码分块约 30 秒 |
| 显存 | 采样峰值整卡 15221 MiB |

抽帧初看：身份、眼镜、衣着稳定，表情比 InfiniteTalk 更丰富、嘴张得更大、露齿笑较多；是否过度夸张需人工判断。与 InfiniteTalk 对比：同一段 4.4 秒配音，InfiniteTalk 用 4 步蒸馏 LoRA 约 2 分钟，Hunyuan 30 步约 14 分钟，Hunyuan 没有官方蒸馏加速版。

## LongCat Avatar 1.5 验证结果｜2026-09-16 19:04

输出 `productions/math/tests/avatar/out/longcat-avatar-mom-test.mp4`，抽帧条 out/frames/longcat-strip.png。配置 longcat-avatar-mom-test.json：预算 832×480、93 帧、8 步 distill、guidance 1.0、种子 42。输出 544×736、25fps、93 帧 3.72 秒，AAC；队列 2 分 37 秒，去噪 8 步约 14 秒/步，采样峰值 10907 MiB。蒸馏 LoRA 经 loras/longcat_avatar_v1_5/dmd_lora.safetensors 硬链接正常加载，未触发联网下载。问题：93 帧只覆盖 3.72 秒，配音 4.38 秒被截断。**复测（19:10，113 帧）**：输出 longcat-avatar-mom-test(2).mp4，544×736、113 帧 4.52 秒，配音完整；队列 3 分 05 秒，采样峰值 10945 MiB；抽帧条 out/frames/longcat-113-strip.png。结论：LongCat 1.5 用 113 帧覆盖 4.4 秒配音，速度仍与 InfiniteTalk 同一量级。

## 三套口型模型横向对比（同一参考图、同一段 4.38 秒中文配音、种子 42、sage2、profile 4）

| 模型 | 配置 | 输出 | 队列耗时 | 采样峰值整卡显存 | 抽帧初看 |
| --- | --- | --- | --- | --- | --- |
| InfiniteTalk 14B INT8 + lightx2v 4 步 LoRA | 480×640、113 帧、两窗 | 480×640、4.52 秒、配音完整 | 2 分 10 秒 | 8034 MiB | 身份稳定，表情克制，嘴开合适中 |
| Hunyuan Avatar 13B INT8 | 预算 832×480、129 帧、30 步 | 544×736、5.16 秒、配音完整 | 14 分 11 秒 | 15221 MiB | 身份稳定，表情最丰富，露齿笑多 |
| LongCat Avatar 1.5 13.6B INT8 + DMD 蒸馏 8 步 | 预算 832×480、113 帧、8 步 | 544×736、4.52 秒、配音完整 | 3 分 05 秒 | 10945 MiB | 身份稳定，眉眼表情变化大，有惊讶/皱眉帧 |

初步判断：速度与质量的折中最好的是 InfiniteTalk（有蒸馏 LoRA，两分钟一条，支持长视频滑窗）；LongCat 1.5 速度接近但默认 93 帧短于配音，需按音频时长设帧数（已把测试配置改为 113 帧待复测）；Hunyuan 表情最活但慢 6 倍且显存最高，适合短特写镜头。最终取舍要看人工验收的口型对齐和"数学妈妈"角色气质。

## 音频栈（2026-09-16 16:50 起）

目标组合：角色配音用 Index TTS 2 克隆声线；无人声背景音乐用 Stable Audio Open 3 Small；歌曲用 ACE-Step 1.5 Turbo（1.7B LM，8 步）；音效按画面用 MMAudio v2。四者都是 Wan2GP 内置模型，只需下载权重，不新增环境。

- 文件清单：由各处理器 `query_model_files` 与 defaults/*.json 的 URLs、text_encoder_URLs 在本地导出（不联网），能选 INT8 的取 INT8。共 56 个文件、22.87 GiB，仓库 DeepBeepMeep/TTS（提交 864a479c）与 DeepBeepMeep/Wan2.1（提交 850ed9ff），已写入 model-manifest.json，总清单 127 文件、100.90 GiB。
- 下载：16:50 用 `--only` 另起进程并行（日志 logs/avatar-audio-download.log），与口型模型共用带宽，会拖慢 Hunyuan/LongCat 约一半。
- MMAudio 配置：wgp_config.json 里 audio_processors.mmaudio.mode=1 对应 v2 检查点，只下载 v2，不下载备用的 gold 版本。
- 许可（商用前逐个核对原始仓库）：IndexTTS2 为自定义 Bilibili 模型许可，达到 1 亿月活或年收入人民币 10 亿元以上时需另行书面许可，并需独立取得参考声音授权；Stable Audio 的代码与模型许可分开，实际 Open 3 Small 检查点须确认适用 Stability 社区许可（其当前商业阈值为年收入 100 万美元）；ACE-Step 1.5 当前为 MIT；MMAudio 代码 MIT，但官方预训练权重为 CC BY-NC 4.0，不能进入当前商业发布母版。DeepBeepMeep 转换版本不改变上游许可。制作分工与来源链接见 `market/英语/07-音频四件套制作方案.md`。
- 状态：下载中。验证顺序：Index TTS 2 用妈妈台词出一段中文配音并与系统合成音对比；Stable Audio 出 30 秒无人声垫乐；ACE-Step 出一段中文短歌；MMAudio 给 InfiniteTalk 样片配环境音。
- **Index TTS 2 已验证（17:17）**：两句中文台词、种子 42，输出 out/tts-indextts2-mom-test.wav，22050Hz 单声道 8.38 秒；队列 58.7 秒（含首次加载），采样峰值整卡显存 4195 MiB。样音是系统合成声，只证明流程可用；音色像不像、断句是否自然待人工听。
- **Stable Audio Open 3 Small 已验证（17:33）**：30 秒无人声垫乐、8 步、种子 42，输出 out/music-stableaudio3-bgm-test.wav；队列 21.6 秒（含加载），采样峰值整卡显存 3627 MiB。是否贴合"儿童数学课"氛围、能否无缝循环待人工听。
- **ACE-Step 1.5 Turbo LM 1.7B 已验证（17:58）**：中文歌词 60 秒、8 步、种子 42，输出 out/song-acestep15-test.wav，48kHz 立体声 60 秒；队列 3 分 12 秒（LM 元数据阶段约 3 分钟占大头，扩散 8 步很快），采样峰值整卡显存 9435 MiB。歌词咬字、旋律是否适合儿童待人工听。
- **MMAudio v2 已验证（18:34）**：mode=edit_remux 对 infinitetalk-mom-test(2).mp4 按画面生成环境音，输出 out/infinitetalk-mom-test(2)_post.mp4（AAC 44.1kHz 单声道，平均 -26 dB）；队列 35 秒，采样峰值整卡显存 6226 MiB。注意：remux 把原配音音轨整体替换为生成音轨，正式流程应先导出生成音轨再与配音、垫乐混音，不能直接用 _post 文件；且 MMAudio 官方权重为 CC BY-NC 4.0，只能内部比较。
- 音频四件套至此全部跑通（Index TTS 2、Stable Audio 3 Small、ACE-Step 1.5 Turbo、MMAudio v2），耗时都在 1 到 3.5 分钟内，峰值显存最高 9.4 GB，与口型模型可在同一台机器上串行使用。
- 测试队列脚本 tools/avatar/run-test-queue.ps1：把多份配置按顺序在 GPU 上逐个执行（绝不并行），日志 logs/avatar-test-queue.log；用 -File 启动时多份配置用逗号连成一个参数。
- 测试配置已写好并通过 `--dry-run`（productions/math/tests/avatar/）：tts-indextts2-mom-test.json（样音暂用系统合成的 mom-test-zh.wav，只验证流程，正式声线需真人样音 10–30 秒）、music-stableaudio3-bgm-test.json（30 秒、8 步）、song-acestep15-test.json（中文歌词 60 秒、8 步、LM 中等思考模式）、sfx-mmaudio-infinitetalk-test.json（mode=edit_remux，对现有样片配环境音）。这些是安装验证配置；英语生产基线改为 E01 的 IndexTTS2 对白、ACE-Step 104 BPM/C 大调/约 37 秒器乐循环、Stable Audio 短音效，以及只供内部比较的 MMAudio 拟音。运行方式同口型测试：`run-avatar-test.ps1 -Settings <json>`。

## 角色一致性实验：VACE FusioniX 14B（2026-09-18 起）

目的：验证"参考图锁角色 + Blender 线稿锁几何"。Fun Control 5B 的 ref_image 是全局参考，会把参考图白底带进场景；VACE 的 image_refs 是主体参考（People / Objects），并默认去除参考图背景。

- 模型：defaults/vace_14B_fusionix.json = FusioniX 蒸馏 T2V 14B 底模（Wan14BT2VFusioniX_quanto_bf16_int8，13.53 GiB）+ VACE 14B 控制模块（wan2.1_Vace_14B_module_quanto_mbf16_int8，3.51 GiB），文本编码器、xlm-roberta、VAE 复用已有文件。清单已加入两文件并下载（logs/avatar-vace-download.log），总清单 129 文件 117.94 GiB。选 FusioniX 而非原版 VACE 14B：10 步、无 CFG，速度约为原版三分之一；原版需 15–30 步 + CFG。
- 控制方式：Wan2GP 对 Blender 平光预览自行做预处理。video_prompt_type 字母：E=Canny 边缘、S=Shapes 线稿、D=深度、P=人体姿态、U=原样、V=有控制视频、I=人物/物体参考图、K=风景参考。测试两条：EVI（Canny + 参考图）与 SVI（Shapes + 参考图），其余参数按 FusioniX 模板：832×480、49 帧、10 步、guidance 1、flow_shift 2、种子 42。
- 配置：productions/math/tests/avatar/vace-fusionix-figure-canny.json、vace-fusionix-figure-shapes.json。
- **结果（14:18）**：两文件 SHA256 校验通过；两条均一次成功。

| 配置 | 队列耗时 | 采样峰值整卡显存 | 身份 | 几何 |
| --- | --- | --- | --- | --- |
| EVI（Canny + 参考图） | 171.8 秒（含首次加载） | 8938 MiB | **很准**：短发、圆眼镜、青色衬衫、米色裤、工具腰包全部对上，是目前所有实验里最接近角色表的一次 | 围栏与相机大致跟随，但人物被放大到远超人偶轮廓，站在剪角后方 |
| SVI（Shapes + 参考图） | 128.3 秒 | 8938 MiB | 小人偶被画成蓝衣路人，不是妈妈；最后 10 帧妈妈以大尺寸从画面右侧"冒出" | 围栏、剪角、相机环绕严格跟随 |

  结论：VACE 的主体参考能力可用且远强于 Fun Control 5B；参考主体与控制视频里"该主体的位置"之间的绑定取决于轮廓大小，人偶在画面里太小时模型要么放大主体（Canny），要么把主体另放一处（Shapes）。输出与抽帧在 productions/math/tests/depth/fence-v002-figure/result/。
- **中景复测（14:29，fence-v003-figure-medium）**：Blender 脚本加 `--focus-figure`，相机距人偶 5 单位、环绕 40°，人偶约占画面高度三分之二。EVI + 参考图，队列 136.1 秒，采样峰值 9427 MiB。结果：妈妈的发型、圆眼镜、青色衬衫、米色裤、工具腰包与角色表一致；人物站在人偶所在位置，按人偶动画转身并在后段抬手挥动；围栏柱子和横杆按 Blender 几何排列，背景草地天空由提示词补齐，整段无闪烁。**这是第一次同时做到身份、位置、动作、几何四项可控。** 输出 productions/math/tests/depth/fence-v003-figure-medium/result/。
- 由此确定角色镜头的基线：Blender 人偶中景（人物占画面不小于二分之一）→ 平光预览 → Wan2GP VACE FusioniX `EVI` + 角色参考图，49 帧约 2 分钟。远景全景仍用 Fun Control 或 VACE 的 Shapes 模式只控几何、不放角色。

## 本次核查发现的问题（15:10 记录，处理情况见上节）

1. 下载清单缺共享文件。Wan2GP 每次加载任何模型前都会先检查一组共享资产（wgp.py `query_core_shared_model_files` 与 MatAnyone 定义）：pose、scribble、flow、depth、wav2vec、roformer、pyannote、mask 等目录，共 21 个文件、4.09 GiB，不在 model-manifest.json 中。缺失时会在首次加载模型时用 huggingface_hub 直接下载，而本机这条路径此前会停滞。需要把这些文件加入清单用同一分块下载器补齐，否则首次生成会卡在下载。
2. LongCat 蒸馏 LoRA 路径不对。清单把 dmd_lora.safetensors 放在 ckpts/longcat_avatar_v1_5/，但源码在生成时按 loras/longcat_avatar_v1_5/dmd_lora.safetensors 查找（wgp.py `get_lora_local_path` + longcat_handler `get_lora_dir`），找不到会再次联网下载。下载完成后需复制或移动到 loras 目录。
3. 配置文件被服务覆盖。上次对 wgp_config.json 写入的 transformer_types、last_model_type、deepy_enabled=0、enhancer_enabled=0 已丢失：服务在 14:52 保存工作区时用运行中的配置重写了文件，当前 transformer_types 为空、deepy_enabled=1、enhancer_enabled=5。要生效必须先停服务再改，或者直接在界面里选模型。原始默认配置保留在 wgp_config.initial.json。
4. 残留缓存。ckpts/.cache/huggingface/download 下有两个 14:27 的 .incomplete 文件（约 1.2 GB）和两个 .lock，是改用分块下载前 huggingface_hub 停滞留下的，可在下载全部完成后删除。
5. ComfyUI 仍在运行（11:27 启动，占用约 3.2 GB 显存、2.6 GB 内存）。做口型生成验收前按原则先停掉，避免和 14B 模型争显存。

## 试错

1. 内置 Git 缺少 remote-https，改为 GitHub 固定提交 ZIP 下载并保留提交号。
2. 普通网络请求受到沙箱限制；通过工具授权的联网安装执行。
3. huggingface_hub 大文件连接停滞、小范围请求可用，改用 16MiB 分块、每文件四路、同时两文件，保留分块以便恢复；完整组装后验证仓库 SHA256，成功才清理本次分块缓存。
4. 不安装可选 DLSS、远程助手或账户集成；本任务只需要本地口型生成。
5. 首次启动要求配置含完整默认字段：先让程序生成标准配置（备份为 wgp_config.initial.json）再改。改动在服务运行中被覆盖，见上节第 3 条；后续改配置一律先停服务。
6. 清单核对方法：以各处理器 `query_model_files` 与 defaults/*.json 中 URLs、modules 为准逐项比对，发现共享资产与 LoRA 路径两处遗漏（上节第 1、2 条）。

## 目录和运行

- 程序：tools/avatar/Wan2GP
- 模型：tools/avatar/Wan2GP/ckpts
- 恢复下载：用含 huggingface_hub 和 requests 的 Python 运行 tools/avatar/download-models.py --download；本次使用现有 ComfyUI Python 执行下载，不修改其依赖。
- 启动：项目根目录 start-avatar.bat 或 start-avatar.ps1。
- 停止前台运行：在启动窗口按 Ctrl+C。
- 同一时刻只执行一套 GPU 生成任务，生成前释放 ComfyUI 的已加载模型。

## 待验收

依赖导入、UI 可达、三套完整模型清单校验、每套至少一个可播放短片、峰值内存/显存与耗时。数学角色的口型观感与身份一致性单独验收，不由程序成功退出代替。

