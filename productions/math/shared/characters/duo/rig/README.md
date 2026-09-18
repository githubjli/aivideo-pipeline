# duo 角色骨骼资产（Mixamo 路线）

把 Mixamo 下载的 FBX 放在本目录，文件名按下面约定，脚本 `tools/blender/render-rigged-shot.py` 会直接读取。

## 下载清单（mixamo.com，需要 Adobe 账号登录）

1. 角色（Characters 页）：选一个卡通感的女性角色作为妈妈（推荐 Michelle、Kaya、Jasmine 之一），下载设置：
   - Format：FBX Binary(.fbx)
   - Pose：T-pose
   - 勾选 With Skin
   - 保存为 `mom-character.fbx`
2. 动作（Animations 页，先选中上面的角色再搜动作），每个动作下载设置：
   - Format：FBX Binary(.fbx)
   - Skin：Without Skin
   - Frames per Second：30
   - Keyframe Reduction：none
   - 保存文件名：
     - Waving → `anim-waving.fbx`
     - Standing Idle → `anim-idle.fbx`
     - Walking（勾选 In Place）→ `anim-walking.fbx`
     - Talking → `anim-talking.fbx`
     - Pointing → `anim-pointing.fbx`
3. 孩子角色以后按同样方式下载为 `kid-character.fbx`，动作可复用（Mixamo 会自动重定向）。

## 目录约定

```text
rig/
  mom-character.fbx      带蒙皮的角色（T-pose）
  kid-character.fbx      以后补
  anim-*.fbx             不带蒙皮的动作
```

## 许可

Mixamo 角色与动作可免费用于个人和商业项目（Adobe 通用使用条款），但不能单独再分发这些 FBX 文件，所以本目录已在 .gitignore 里排除，仓库只保留这份说明。
