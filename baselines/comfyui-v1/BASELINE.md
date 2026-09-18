# ComfyUI 基线 v1（冻结于 2026-09-18）

这是"初始版本"快照：此后任何升级 ComfyUI、依赖、模型或工作流的操作，都先与本目录比对；出问题时按下面的恢复步骤回到本状态。本目录只保存脚本、工作流与校验记录，不复制模型和程序本体。

## 版本

| 组件 | 版本 / 标识 |
| --- | --- |
| ComfyUI 便携包 | v0.36.0 NVIDIA 版，安装包 SHA256 `c3c60192840f8b68c9a47cf3e8161ecb108e5ffdf5ea236c1c72a402e442695d`（downloads/ComfyUI_windows_portable_nvidia.7z） |
| 内置 Python | 3.13.14 |
| PyTorch | 2.13.0+cu130，torchvision 0.28.0+cu130 |
| 前端 comfyui-frontend-package | 1.52.7 |
| 模板 comfyui-workflow-templates / -json | 0.11.62 / 0.1.85 |
| 第三方自定义节点 | 无（custom_nodes 只有官方示例文件） |
| 完整依赖清单 | records/python-packages-2026-09-18.txt（pip freeze） |

## 模型（全部 SHA256 校验通过，见 records/model-verification.json）

| 文件 | 目录 | 大小 | 仓库提交 |
| --- | --- | --- | --- |
| sd_xl_base_1.0.safetensors | checkpoints | 6.46 GiB | stabilityai/stable-diffusion-xl-base-1.0 @ 46216598… |
| wan2.2_ti2v_5B_fp16.safetensors | diffusion_models | 9.31 GiB | Comfy-Org/Wan_2.2_ComfyUI_Repackaged @ c4f60d30 |
| wan2.2_fun_control_5B_bf16.safetensors | diffusion_models | 9.32 GiB | 同上 |
| umt5_xxl_fp8_e4m3fn_scaled.safetensors | text_encoders | 6.27 GiB | 同上 |
| wan2.2_vae.safetensors | vae | 1.31 GiB | 同上 |

## 工作流（workflows/，同时放在 ComfyUI 用户工作流目录）

| 名称 | 用途 | 状态 |
| --- | --- | --- |
| 01-sdxl-image | 文生图基线 | 已验证 |
| 02-wan-text-to-video | 文生视频基线 | 已验证 |
| 03-wan-image-to-video | 图生视频基线 | 已验证 |
| 04b-wan-fun-control-canny | Blender 线稿控制视频（推荐） | 已验证 |
| 04 / 04c | 深度图控制（对照，对该模型无效） | 已验证无效 |
| 04d / 04e | 线稿 + 3D 人偶（04e 加角色参考图） | 见 docs/blender-linework-pipeline.md |

## 恢复到本基线

1. ComfyUI 程序：若被升级或损坏，用 downloads 里的安装包重新解压（先核对上表 SHA256），不要运行 update 目录里的更新脚本。
2. 依赖：`python_embeded\python.exe -m pip freeze` 与 records/python-packages-2026-09-18.txt 比对；不一致时按该文件回装。
3. 模型：`python -X utf8 -s verify-models.py` 重新校验；缺失的按 records 里的元数据从同一仓库提交重新下载。
4. 工作流与脚本：把本目录 workflows/ 与 scripts/ 复制回项目根目录对应位置，或重新运行 prepare-workflows.py 从官方模板再生成。
5. 验证：依次运行 01、02、04b 三条工作流，与 DEPLOYMENT.md 记录的耗时、显存和输出比对。

## 变更规则

- 升级任何组件前，先在本目录之外新建 comfyui-v2 快照，再改；v1 目录只读。
- 不安装第三方自定义节点，除非某个能力核心节点确实没有；安装时记录节点仓库提交号。
