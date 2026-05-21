# AI Collaboration Concept Boundaries

## Purpose

This topic records the durable boundary between rules, skills, constitution files, topics, plans, specs, PR bodies, and comments. The goal is to keep each concept single-purpose and prevent future changes from moving the same truth into multiple carriers.

## Core Categories

| Concept | Carrier | Role | Must not contain |
|---------|---------|------|------------------|
| Workflow rules | `.ai/skills/ai-collaboration-workflow/SKILL.md` | Non-bypassable coding-agent principles, AI-first collaboration rules, HIL, worktree gate, review stance, skill-use discipline, and quality / scope gates | Specialist task procedures, agent-specific mechanics, task-specific execution logs, project runtime commands or language preferences |
| Workflow skill | `.ai/skills/ai-collaboration-workflow/SKILL.md` | Executable repository workflow: startup, unified decision protocol, artifact vocabulary, Superpowers handoff, validation, knowledge closeout, and final handoff | Specialist task procedures |
| Scaffold skill package | `ai-collaboration-workflow` distribution assets | Install or update the runtime `.ai/` collaboration scaffold in another repository | Project-specific architecture, product facts, runtime dependency on this template repository |
| Runtime scaffold | Repository root `.ai/` plus entry files | The installed truth-source paths agents read during work | Source-package-only relative links or assumptions about this template repository's checkout path |
| Specialist skills | `.ai/skills/<skill>/SKILL.md` or optional `skills/<skill>/SKILL.md` | Task-specific procedures, tools, domain workflows | Behavior constraints or human-agent collaboration rules owned by other carriers |
| Agent entry files | `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` | Agent-specific bootstrap and pointers | Duplicated constitution or skill bodies |
| Topic docs | `.ai/topics/<slug>/` | Durable design rationale, boundary decisions, roadmap | Agent rule arbitration, local execution checklist |
| Project style docs | `docs/references/<style>.md` | Project or template language preferences | Cross-agent behavior constraints or quality gates |
| Local specs / plans | `.ai/superpowers/specs/`, `.ai/superpowers/plans/active/` | Gitignored design drafts and single-run execution plans | Durable team truth that must survive across sessions |
| PR body / comments | Current PR | PR-specific goal, design, validation, risk, and review resolution | Long-lived architecture or collaboration rules |

## Placement Tests

Use these tests before adding or moving collaboration text:

- If the sentence constrains coding-agent behavior regardless of collaboration flow, put it in `ai-collaboration-workflow/SKILL.md`.
- If the sentence governs how the user and coding agent collaborate, how lifecycle gates run, or how the repository workflow proceeds, put the normative rule in `ai-collaboration-workflow/SKILL.md`.
- If the sentence teaches a specialized technique or tool flow, put it in the relevant specialist skill.
- If the sentence explains why a boundary exists or compares alternatives, put it in a topic design document.
- If the sentence only describes the current PR, put it in the PR body or review thread.
- If the sentence is a temporary execution checklist for the current run, put it in the active local plan.

## Common Confusions

| Confusion | Resolution |
|-----------|------------|
| Collaboration laws vs quality gates | Collaboration laws say how the agent must work; quality gates say what evidence and risk checks are needed before completion. Both live in `ai-collaboration-workflow/SKILL.md`, but they must stay separate sections. |
| Quality gates vs project style | Quality and scope gates belong in `ai-collaboration-workflow/SKILL.md`; language/tool preferences such as package manager or data libraries belong in the consuming repository's architecture / language-style doc. In this template: `docs/references/project-overview.md` + `docs/references/python-code-style.md`. |
| Behavior constraint vs collaboration rule | Both belong in `ai-collaboration-workflow/SKILL.md`: behavior constraints limit the coding agent in every context; collaboration rules govern the workflow between user and coding agent. |
| Skill package vs installed `.ai` runtime | The portable skill package ships behavior constraints and collaboration rules. The target repository still has local `.ai/feedback/`, `.ai/topics/`, and `.ai/superpowers/` runtime artifact directories after installation. |
| Skill invocation vs skill routing table | The workflow skill hands off to `using-superpowers`; it should not duplicate a routing table for every specialist skill. |
| Handoff checkpoint vs skill workflow | The workflow skill defines the handoff point to `using-superpowers`; downstream skill choice and procedures stay inside Superpowers. |
| `SKILL.md` vs `references/` | `SKILL.md` is the always-loaded operating guide and rule body. `references/` is reserved for optional heavy reference material, not mandatory behavior rules. |
| Entry-file pointers vs duplicate truth sources | Entry files point to the workflow skill and may own startup / navigation / cognitive-posture reminders. Those entry-owned paragraphs must not be duplicated elsewhere. |
| Sibling worktree vs local override | The concrete default carrier is owned by the agent entry files; other docs should not repeat the path. Use another path only when the user or repository rules specify it. |
| Target worktree vs other checkout | Before any behavior that can create modifications, confirm the current path, branch, and worktree belong to the task. If a target worktree exists, only that worktree may receive writes. Other checkouts are read-only for locating context; if an agent writes there by mistake, it must migrate its own changes to the target worktree and clean the mistaken checkout. |
| Workflow orchestration vs task execution | `ai-collaboration-workflow` owns human-AI collaboration, topic / roadmap, task decomposition, HIL, worktree, artifacts, validation, publish, and closeout. Superpowers owns concrete task execution methods. After each Superpowers run, control returns to workflow for repository-level decisions. |
| Artifact vocabulary vs artifact routing rule | Both belong in `SKILL.md`; vocabulary explains carriers, while the decision protocol governs routing decisions. |
| Topic design vs local spec | Topic design is tracked and durable; local spec is an ignored draft. Stable conclusions from a local spec must be moved into a tracked carrier before merge. |
| Current-state rule vs history logs | Rules, README, and design body sections describe current state; roadmap, decisions, and Provenance may record dated history. |
| Knowledge closeout vs validation | Validation proves the change works; knowledge closeout moves durable decisions to the right carrier. Both happen before publishing. |
| Review reply vs team-external notification | Replying to PR review threads is normal PR maintenance; irreversible or external publication gates cover higher-risk actions such as push, merge, release, or team-external notification. |
| File split vs same-owner consolidation | Prefer one clear owner file until the content has a different audience, lifecycle, truth-source layer, permission boundary, or maintenance cadence. If a new file cannot pass one of those tests, merge it into the existing carrier and split later when it becomes hard to navigate. |

## Maintenance Controls

These controls guide document placement. If a control must become a coding-agent behavior constraint, move the rule body into `ai-collaboration-workflow/SKILL.md` and keep only a pointer here.

1. Keep `ai-collaboration-workflow/SKILL.md` focused on coding-agent behavior constraints, human-agent collaboration rules, hard quality gates, and workflow startup mechanics.
2. Keep portable skill references in repository-root form, such as `.ai/feedback/README.md`; avoid relative links that only work from the skill's current install location.
3. Keep mandatory rules in `SKILL.md`; move material to `references/` only when it is optional background or heavy task-specific reference material.
4. Handoff to `using-superpowers`; do not copy or route downstream Superpowers skill procedures in the workflow skill.
5. Keep agent-specific mechanics out of the constitution package and workflow skill. Agent-specific details belong in entry files or adapter directories.
6. When entry files and the workflow skill conflict, update entry files to match `ai-collaboration-workflow/SKILL.md`.
7. When a review comment creates durable design knowledge, record the conclusion in a tracked topic before treating the thread as resolved.
8. Keep project or language-stack preferences in project docs, not workflow references.
9. Before adding a new documentation or rule file, identify the existing carrier that could absorb the content; create the file only when the boundary is stronger than convenience or cosmetic organization.
