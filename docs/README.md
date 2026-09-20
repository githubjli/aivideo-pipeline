# 文档地图

按"先看什么、再看什么"排列。所有文档都记录实测数字，未验证的内容明确标"待验收"。

| 顺序 | 文档 | 内容 | 读者 |
| --- | --- | --- | --- |
| 1 | [../README.md](../README.md) | 项目入口：怎么启动、怎么跑一条镜头、目录在哪 | 所有人 |
| 2 | [phase-1-summary.md](phase-1-summary.md) | 第一阶段总结：做成了什么、实测数据、决策、遗留问题、下一阶段 | 决策与回顾 |
| 3 | [shot-pipeline.md](shot-pipeline.md) | 镜头流水线使用说明：一个 JSON 说明书生成一条带配音、动作、口型的镜头 | 日常制作 |
| 4 | [blender-linework-pipeline.md](blender-linework-pipeline.md) | Blender 线稿 / 人偶 / 参考图控制的实现记录与全部对照实验 | 想改流程的人 |
| 5 | [../tools/avatar/DEPLOYMENT.md](../tools/avatar/DEPLOYMENT.md) | Wan2GP 运行器：口型三套、音频四件套、VACE、Multitalk 的部署、模型清单、加速、试错 | 维护环境的人 |
| 6 | [../DEPLOYMENT.md](../DEPLOYMENT.md) | ComfyUI 侧：硬件、便携包、SDXL / Wan 2.2 基线、Fun Control 深度与线稿实验 | 维护环境的人 |
| 7 | [../baselines/comfyui-v1/BASELINE.md](../baselines/comfyui-v1/BASELINE.md) | 冻结的 ComfyUI 初始版本：版本号、模型 SHA256、恢复步骤 | 出问题时 |
| 8 | [../productions/math/shared/characters/duo/rig/README.md](../productions/math/shared/characters/duo/rig/README.md) | Mixamo 骨骼角色的下载清单与命名约定 | 准备资产的人 |

## 约定

- 每次环境、模型、参数或流程变更，先改对应文档再提交；失败也记录。
- 生成结果只写"程序跑通、音视频完整"等可验证事实；口型对齐、音色、表情之类主观项单列"待人工验收"。
- 权重全部锁定仓库提交号与 SHA256，清单在 `tools/avatar/model-manifest.json` 与 `downloads/*.json`。
- 测试素材、控制视频、生成结果按镜头归档在 `productions/math/tests/depth/<镜头>/` 或 `productions/math/shots/<镜头>/`，不入 git。
