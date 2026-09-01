# Change Log

This file is the entry index for the bilingual monthly records under
[`changelog/`](changelog/). Detailed file paths, line numbers, and diffs remain
in the monthly record; this index keeps the latest five version entries easy to
find.

## Archive

- [2026-09](changelog/2026-09.md)
- [2026-08](changelog/2026-08.md)

## Recent Versions

### v0.3.1 (2026-09-01) - codex

- [env] [完成] 修复 RoboTwin20 的 SAPIEN `pkg_resources` 兼容性并验证仿真依赖导入，保持碰撞规划源码不变。
- [env] [completed] Fixed RoboTwin20 SAPIEN `pkg_resources` compatibility and verified simulator imports without changing collision-planning source.
- Details: [2026-09 monthly record](changelog/2026-09.md#v031-2026-09-01-0020---codex)

### v0.3.0 (2026-09-01) - codex

- [sense] [完成] 在独立 `paos-perception-manipulation` 工程实现 provider-neutral `scene.observe` Query、无运动 Fake Gateway 和 7 项 PAOS 客户端一致性测试。
- [sense] [completed] Implemented provider-neutral `scene.observe`, a no-motion Fake Gateway, and seven PAOS client conformance tests in the independent `paos-perception-manipulation` project.
- Details: [2026-09 monthly record](changelog/2026-09.md#v030-2026-09-01-0000---codex)

### v0.2.0 (2026-08-31) - codex

- [env] [完成] 重建官方 RoboTwin 2.0 源码和独立 `RoboTwin20` 环境。
- [env] [completed] Recreated official RoboTwin 2.0 source and isolated `RoboTwin20` environment.
- Details: [2026-08 monthly record](changelog/2026-08.md#v020-2026-08-31-1705---codex)

### v0.1.15 (2026-08-31) - codex

- [docs] [完成] 修正 Session 生命周期、阶段结果投影和单能力 PR 拆分，并锁定 `scene.observe` 为首个实现功能。
- [docs] [completed] Corrected Session lifecycle, phase-result projection, and one-capability PR splitting; locked `scene.observe` as the first implementation capability.
- Details: [2026-08 monthly record](changelog/2026-08.md#v0115-2026-08-31-1652---codex)

### v0.1.14 (2026-08-31) - codex

- [docs] [完成] 收口 Hephaestus 感知抓取链路的 PAOS 模块化接口边界，并增加阶段结算归因审核。
- [docs] [completed] Tightened the PAOS modular boundary for the Hephaestus perception-grasp chain and added phase-settlement attribution review.
- Details: [2026-08 monthly record](changelog/2026-08.md#v0114-2026-08-31-1612---codex)

### v0.1.13 (2026-08-31) - codex

- [docs] [完成] 将 fork、`upstream/main`、Forge worktree 和首个功能分支创建流程保存到 PR 文档。
- [docs] [completed] Saved the fork, `upstream/main`, Forge worktree, and first feature-branch workflow in the PR document.
- Details: [2026-08 monthly record](changelog/2026-08.md#v0113-2026-08-31-1520---codex)

### v0.1.12 (2026-08-31) - codex

- [chore] [完成] 准备独立 Forge worktree，并验证双远程和官方 `main` 基线。
- [chore] [completed] Prepared the isolated Forge worktree and verified the two remotes and official `main` baseline.
- Details: [2026-08 monthly record](changelog/2026-08.md#v0112-2026-08-31-1445---codex)

### v0.1.11 (2026-08-31) - codex

- [docs] [完成] 锁定 `origin/main` Forge v1.0 为融合基线，按 PR0-PR8 拆分 Hephaestus 能力，并限制为低影响 capability 扩展。
- [docs] [completed] Lock `origin/main` Forge v1.0 as the fusion baseline, split Hephaestus capabilities into PR0-PR8, and constrain the work to low-impact capability extensions.
- Details: [2026-08 monthly record](changelog/2026-08.md#v0111-2026-08-31-0000---codex)
