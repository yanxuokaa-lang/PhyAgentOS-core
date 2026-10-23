# PAOS laboratory scene patches

PAOS owns these scene changes. LabUtopia supplies the locally installed USD
assets and preview/build tools. Apply patches in that working tree without
creating commits or pushing to the external LabUtopia repository.

这些场景修改在 PAOS 中管理。LabUtopia 提供本地 USD 资产、构建和预览工具；
在其工作区应用补丁即可，不向外部 LabUtopia 仓库提交或推送。

## Glass rod in the existing rack

`labutopia-tabletop-rod-storage.patch` updates the original station opened by
`python scripts/preview_tabletop_station.py --view third-person`. It moves the
250 mm glass rod from the outer tabletop into an empty rack hole near the work
area. Eight labeled R01–R08 flasks, the beaker, six tubes and camera configuration
retain their layout. The patch includes config, builder, generated USD text and
the scene document. It does not contain benchmark actions or grasp predictions.

补丁将玻璃棒放入原场景试管架靠操作区的空孔，保留八个带标签锥形瓶、烧杯、
六支试管与相机配置。它包含配置、构建器、生成的 USD 文本和说明；初始摆位
仅用于场景构建，不能作为 PAOS 抓取点。抓取仍需通过相机感知和 GraspNet。

The local `/home/yanxu/LabUtopia` working tree already has this patch applied.
Do not apply it twice. For another checkout with the same original station,
replace the paths below with the local PAOS and LabUtopia locations:

当前本机已应用该补丁。其他具有同一原场景的工作区可按下面命令复现。
USD uses Git LFS; disable its clean filter for this text-patch operation only.
This does not modify Git configuration or stage the external files.

```bash
cd /home/yanxu/LabUtopia
git -c filter.lfs.process= -c filter.lfs.required=false apply --check /home/yanxu/PhyAgentOS-forge/examples/forge-adapters/isaacsim_lab/patches/labutopia-tabletop-rod-storage.patch
git -c filter.lfs.process= -c filter.lfs.required=false apply /home/yanxu/PhyAgentOS-forge/examples/forge-adapters/isaacsim_lab/patches/labutopia-tabletop-rod-storage.patch
```

For an already applied patch, use `apply --reverse --check` with the same options
to verify its presence; do not run a second forward apply. If the check fails,
inspect local file differences before applying; do not overwrite local changes.

Activate the existing `labutopia` environment and run:

```bash
python scripts/build_tabletop_station.py build
python scripts/build_tabletop_station.py inspect
python scripts/preview_tabletop_station.py --view third-person
```

Static checks on October 23, 2026: support gap 0.2 mm; radial clearance 8.039 mm
at each guide plate; no overlap with the six tubes. Floating, solid-plate
insertion and hole-edge collision counterexamples were rejected. Third-person
and rack-close-up RTX renders were visually inspected. Scene units are meters,
Z-up. No grasp, actuator command or hardware operation was used for this scene
change. The former 56-pose IK report does not cover the new rod pose.

2026-10-23 静态验证通过：棒底支撑间距 0.2 mm，两层孔板净空各 8.039 mm，
与已有试管无重叠；悬空、插入实体板和碰孔边的反例均被拒绝。已检查第三视角
和架子近景。动态稳定性、GraspNet 抓取、倾倒/搅拌及归位仍属后续集成验收。

Local evidence: `/home/yanxu/LabUtopia/outputs/tabletop-rod-storage/20261023-r1/`.
The PAOS perception refactor and its separate experiment results are not part
of this scene-only commit.
