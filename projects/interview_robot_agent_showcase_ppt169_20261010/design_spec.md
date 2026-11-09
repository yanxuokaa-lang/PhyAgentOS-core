# interview_robot_agent_showcase - Design Spec

## I. Project Information

| Item | Value |
| ---- | ----- |
| **Project Name** | interview_robot_agent_showcase |
| **Canvas Format** | PPT 16:9 (1280 x 720) |
| **Page Count** | 16 |
| **Design Style** | General Consulting + technical documentary |
| **Target Audience** | Robotics, embodied AI, VLA, and Agent systems interviewers |
| **Use Case** | 12-15 minute technical interview project presentation |
| **Created Date** | 2026-10-10 |

## II. Canvas Specification

| Property | Value |
| -------- | ----- |
| **Format** | PPT 16:9 |
| **Dimensions** | 1280 x 720 px |
| **viewBox** | `0 0 1280 720` |
| **Margins** | 56px left/right, 42px top/bottom |
| **Content Area** | x: 56-1224, y: 86-650 |

## III. Visual Theme

### Theme Style

- **Style**: VLA weekly technical-report blue; evidence-led and interview-oriented
- **Theme**: Light
- **Tone**: Evidence-led, engineering-focused, credible, modern

### Color Scheme

| Role | HEX | Purpose |
| ---- | --- | ------- |
| **Background** | `#F3F7FB` | Page background |
| **Secondary bg** | `#FFFFFF` | Panels and media placeholders |
| **Primary** | `#17324D` | Titles, architecture lines, dark panels |
| **Accent** | `#2471B4` | Header bars, key steps, and emphasis |
| **Secondary accent** | `#5B9BD5` | Secondary labels and flow highlights |
| **Body text** | `#17324D` | Main copy |
| **Secondary text** | `#62788E` | Captions and annotations |
| **Tertiary text** | `#62788E` | Footnotes and placeholder labels |
| **Border/divider** | `#C9D9E8` | Dividers and panel borders |
| **Success** | `#2D9D78` | Completed states and validated outcomes |
| **Warning** | `#D95D39` | Blocked, unknown, or recovery states |
| **Pale blue** | `#E8F1F9` | Quiet panels and evidence regions |
| **Cool panel** | `#EEF4F9` | Neutral media placeholders |
| **Deep blue** | `#184CA0` | Strong emphasis and section markers |
| **Soft blue** | `#C6DDF1` | Secondary diagram fills |
| **Slate** | `#44546A` | Supporting technical labels |

### AI Image Strategy

No AI-generated images. Use user-provided photos, videos, official webpage captures, and repository-derived diagrams only. Missing media is represented by clearly labeled placeholders.

## IV. Typography System

### Font Plan

| Role | Chinese | English | Fallback tail |
| ---- | ------- | ------- | ------------- |
| **Title** | `Microsoft YaHei` | `Arial` | `sans-serif` |
| **Body** | `Microsoft YaHei` | `Arial` | `sans-serif` |
| **Emphasis** | `Microsoft YaHei` | `Arial` | `sans-serif` |
| **Code** | — | `Consolas, "Courier New"` | `monospace` |

**Per-role font stacks**:

- Title: `"Microsoft YaHei", Arial, sans-serif`
- Body: `"Microsoft YaHei", Arial, sans-serif`
- Emphasis: `"Microsoft YaHei", Arial, sans-serif`
- Code: `Consolas, "Courier New", monospace`

### Font Size Hierarchy

**Baseline**: Body font size = 20px

| Purpose | Ratio to body | Size | Weight |
| ------- | ------------- | ---- | ------ |
| Cover title | 4x | 80px | Bold |
| Chapter / section opener | 2.5x | 50px | Bold |
| Page title | 1.8x | 36px | Bold |
| Hero number | 2x | 40px | Bold |
| Subtitle | 1.25x | 25px | SemiBold |
| Body content | 1x | 20px | Regular |
| Annotation / caption | 0.7x | 14px | Regular |
| Page number / footnote | 0.55x | 11px | Regular |

## V. Layout Principles

- Use asymmetric compositions: media and evidence dominate where available; text dominates only on architecture and planning pages.
- Use thin dividers, small labels, and rectangular panels with radius no larger than 8px.
- Use one blue identity throughout; distinguish the two projects through titles and content, not competing accent colors.
- Use a consistent 6px blue top rule and restrained footer on content pages, following technical-report conventions.
- Do not use decorative gradients, generic AI illustrations, or unverified metric charts.
- Placeholder media keeps native aspect ratio and includes a replacement label.

## VI. Icon Usage Spec

- **Library**: `tabler-outline`
- **Stroke width**: 2
- **Use**: small supporting marks only; never substitute for video, photo, certificate, or architecture evidence.
- **Inventory**: `camera`, `robot`, `tool`, `route`, `check`, `alert`, `chart-bar`, `video`, `certificate`, `graph`, `refresh`, `shield`

## VII. Visualization Reference List

| Visualization | Reference template path | Used in | Purpose |
| ------------- | ----------------------- | ------- | ------- |
| Pipeline diagram | `no-template-match` | P02, P04, P10, P15 | Show end-to-end data and execution ownership |
| Tool ladder | `no-template-match` | P11 | Map perception and manipulation abilities to Tools |
| Semantic DAG | `no-template-match` | P13 | Show Agent subtask compilation and dependencies |
| State timeline | `no-template-match` | P14 | Show execution, blocked state, recovery, and verification |
| KPI strip | `no-template-match` | P08, P09 | Present confirmed competition outcomes without fabricating rates |

## VIII. Image Resource List

| Filename | Dimensions | Ratio | Purpose | Status | Generation description |
| -------- | ---------- | ----- | ------- | ------ | --------------------- |
| `images/competition_official_site.png` | placeholder | 16:9 | Official event page capture | Placeholder | Replace with official website screenshot |
| `images/competition_group_photo.jpg` | placeholder | 4:3 | Competition team photo | Placeholder | Replace with supplied award photo |
| `images/competition_certificate.jpg` | placeholder | 4:3 | Award certificate | Placeholder | Replace with supplied certificate |
| `media/competition_demo_01.mp4` | placeholder | 16:9 | Sample bottle loading | Placeholder | Replace with supplied video |
| `media/competition_demo_02.mp4` | placeholder | 16:9 | Sample rack insertion | Placeholder | Replace with supplied video |
| `media/competition_demo_03.mp4` | placeholder | 16:9 | Solvent tubing switch | Placeholder | Replace with supplied video |
| `media/competition现场运行.mp4` | placeholder | 16:9 | Competition floor run | Placeholder | Replace with supplied video |
| `images/paos_agent_state.png` | placeholder | 16:9 | Agent intermediate state | Placeholder | Replace with supplied state screenshot |
| `media/paos_block_task.mp4` | 4:3 source | 4:3 | Observer-camera footage of the block task | Supplied | Embedded on P12; Agent call trace screenshot remains pending |

## IX. Content Outline

### Opening

1. **Cover** — *从真实机器人执行，到 Agent 驱动的长程任务规划*; two projects share one loop: perception, tool calling, execution, verification, recovery.
2. **Technical throughline** — competition proves real-world execution; PhyAgentOS proves tool-mediated long-horizon planning.

### Competition: VLA in a real laboratory task

3. **Competition context** — ICRA 2026 WBCD, Jingtai life-science track, official site placeholder, task context and personal responsibility.
4. **System architecture** — global and wrist RGB-D, robot state, language instruction, pi0.5, dual-arm control, 60 Hz control and 15 Hz recording.
5. **Demo 01: sample bottle loading** — video placeholder, key grasp and placement steps, engineering note on filtered actions.
6. **Demo 02: sample rack insertion** — video placeholder, alignment and insertion evidence.
7. **Demo 03: solvent tubing switch** — video placeholder, multi-stage continuous operation.
8. **Competition floor run** — real-run video placeholder plus confirmed 20 minutes, 9 rounds, 760 points.
9. **Award evidence** — group photo and certificate placeholders, China champion and global second in the track.

### PhyAgentOS: concrete Tool-mediated long-horizon planning

10. **Actual PAOS execution boundary** — AgentLoop + Planner → AgentTask / PlanRevision → ForgeToolClient → Gateway `/tools` → ToolInvocation → Endpoint / Dora → evidence and verifier.
11. **Perception algorithms as Tools** — `scene.observe`, `scene.understand`, `manipulation.capabilities`, `grasp.propose`, `manipulation.prepare`, `object.acquire`, `object.place`, `task.verify`; runtime profiles share the contract boundary.
12. **Block arrangement demo** — agent video placeholder with task_id, revision_id, current node, Tool, scene_revision, evidence refs, and next ready nodes.
13. **Agent-composed semantic DAG** — `AgentSubtaskSpec` expands each object relocation into observe → capabilities → understand → grasp → prepare → acquire → place, then joins at `verify`.
14. **Long-horizon execution and recovery** — node terminal facts, blocked/unknown handling, bounded same-task PlanRevision, replay/pause/resume/stop semantics.
15. **Experience attribution and Skill evolution** — AgentTask → redacted episode → failure attribution → LessonCluster / candidate → independent review → workspace Skill revision.
16. **Closing** — two projects, one engineering capability: perception becomes a callable capability, execution produces evidence, and verified outcomes guide the next task.

## X. Speaker Notes Requirements

- Create `notes/slide_XX.md` for each slide.
- Each note includes: one-sentence takeaway, 30-60 second spoken script, evidence boundary, and anticipated follow-up question.
- Notes must label media as `PLACEHOLDER` until user assets are supplied; update supplied assets individually and preserve evidence boundaries.

## XI. Technical Constraints Reminder

- SVG pages are authored by the main agent, one page at a time.
- Re-read `spec_lock.md` before each page.
- Use only locked colors, font stacks, icon library, and image paths.
- No `<style>`, `<class>`, `<foreignObject>`, `<script>`, animations, named HTML entities, or `rgba()`.
- Use raw Unicode arrows and punctuation; escape XML reserved characters.
- Videos are external media placeholders in the SVG/PPTX; keep a `media/README.txt` manifest.
- Do not claim any placeholder media or unprovided benchmark metric as actual evidence.
