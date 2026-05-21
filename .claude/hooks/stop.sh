#!/usr/bin/env bash
# Stop hook: 业界通用协议（参考 andylizf/nonstop 的 stop hook + Claude Code 官方 Stop hook 规范）。
# 触发条件：
#   (1) TaskList 有 pending/in_progress
#   (2) 非琐碎 diff 但无活跃 plan（Iron Law #2）
#   (3) 活跃 plan 缺或空 "## Validation" 段（Iron Law #3 的机械 nudge；证据质量由 reviewer 负责）
#   (4) 活跃 plan 仍有未勾 checkbox（Iron Law #5）
# 返回：`{"decision":"block","reason":"..."}` 强制 Claude 继续；按 Blocker Decision Framework L1/L2/L3 处理阻塞
# 防无限循环：读 stdin JSON 里的 stop_hook_active；同一 turn 已 block 过则放行
# Nudge 上限：TaskList 与 plan 检查共用单 session 累计 block 次数；超过 CC_STOP_MAX（默认 5）时放行；CC_STOP_MAX=0 禁用 hook
set -e

# --- 读 stdin JSON ---
input=$(cat 2>/dev/null || true)

# 兼容：无 stdin / 非 JSON 时走旧逻辑（session_id=default, stop_hook_active=false）
session_id=default
stop_hook_active=false
if [ -n "$input" ]; then
    session_id=$(printf '%s' "$input" | python3 -c 'import json, sys
try:
    value = json.load(sys.stdin).get("session_id", "default")
    print(value if isinstance(value, str) and value else "default")
except Exception:
    print("default")
' 2>/dev/null || echo "default")
    stop_hook_active=$(printf '%s' "$input" | python3 -c 'import json, sys
try:
    value = json.load(sys.stdin).get("stop_hook_active", False)
    print("true" if value is True else "false")
except Exception:
    print("false")
' 2>/dev/null || echo "false")
fi
session_id=$(printf '%s' "$session_id" | tr -cd '[:alnum:]_-')
[ -n "$session_id" ] || session_id=default

# --- 防无限循环：同一 turn 已 block 过则放行（Claude Code 官方防循环约定）---
[ "$stop_hook_active" = "true" ] && exit 0

max_nudges_config="${CC_STOP_MAX:-5}"
case "$max_nudges_config" in
    ''|*[!0-9]*) max_nudges_config=5 ;;
esac

# CC_STOP_MAX=0 explicitly disables this hook.
[ "$max_nudges_config" -eq 0 ] && exit 0

# --- TaskList 状态检测（业界协议：claudefa stop-hook-task-enforcement）---
# 新 Task* tools 的 state 在 ~/.claude/tasks/<session_id>/<task_id>.json；每个 task 一个 JSON
# 有 pending / in_progress 任务 = 本轮未完；即使 plan 全勾也阻止 stop
tasks_dir="$HOME/.claude/tasks/$session_id"
if [ -d "$tasks_dir" ]; then
    active_count=$(TASKS_DIR="$tasks_dir" python3 <<'PY' 2>/dev/null
import glob
import json
import os

c = 0
try:
    for f in glob.glob(os.path.join(os.environ["TASKS_DIR"], "*.json")):
        with open(f) as fh:
            t = json.load(fh)
        if t.get("status") in ("pending", "in_progress"):
            c += 1
    print(c)
except Exception:
    print(0)
PY
)
    if [ -n "$active_count" ] && [ "$active_count" -gt 0 ]; then
        # 走统一 Nudge 计数，防 TaskList 分支绕过上限死锁
        STATE_DIR_EARLY="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/state"
        mkdir -p "$STATE_DIR_EARLY" 2>/dev/null || true
        counter_file_early="$STATE_DIR_EARLY/stop-${session_id}.count"
        max_nudges_early="$max_nudges_config"
        count_early=0
        [ -f "$counter_file_early" ] && count_early=$(cat "$counter_file_early" 2>/dev/null || echo 0)
        count_early=$((count_early + 1))
        echo "$count_early" > "$counter_file_early"
        if [ "$max_nudges_early" -gt 0 ] && [ "$count_early" -gt "$max_nudges_early" ]; then
            rm -f "$counter_file_early"
            exit 0
        fi
        BLOCK_COUNT="$count_early" \
        BLOCK_MAX="$max_nudges_early" \
        ACTIVE_COUNT="$active_count" \
        SAFE_SESSION_ID="$session_id" \
        python3 <<'PY'
import json
import os

reason = f"""[Stop BLOCK nudge {os.environ["BLOCK_COUNT"]}/{os.environ["BLOCK_MAX"]}] TaskList 还有 {os.environ["ACTIVE_COUNT"]} 个 pending/in_progress 任务（~/.claude/tasks/{os.environ["SAFE_SESSION_ID"]}/）。Iron Law #5：计划就绪无阻塞就跑完。

按 Blocker Decision Framework：
  L1 能自解 → 解决这些 task，逐个 TaskUpdate 到 completed
  L2 可 workaround → 做 workaround 并 TaskUpdate
  L3 真 blocked → TaskUpdate status=completed 并在 description 里注明"blocked 移 follow-up 理由" 或 TaskCreate 新的 follow-up 任务

不允许：留 in_progress 任务 turn end；不允许假装任务完成但 status 不更新。"""
print(json.dumps({"decision": "block", "reason": reason}))
PY
        exit 0
    fi
fi

# --- 非琐碎 diff 判定 ---
file_count=$(git status --porcelain 2>/dev/null | wc -l | tr -d '[:space:]')
[ "$file_count" -eq 0 ] && exit 0

unstaged_lines=$(git diff --diff-filter=ACMR 2>/dev/null | wc -l | tr -d '[:space:]')
staged_lines=$(git diff --cached --diff-filter=ACMR 2>/dev/null | wc -l | tr -d '[:space:]')
untracked_count=$(git status --porcelain 2>/dev/null | awk '/^\?\? / {c++} END {print c+0}')
diff_lines=$((unstaged_lines + staged_lines))
if [ "$untracked_count" -gt 0 ]; then
    # Conservative estimate: untracked files have no git diff yet, but still represent work.
    diff_lines=$((diff_lines + untracked_count * 31))
fi
if [ "$file_count" -le 1 ] && [ "$diff_lines" -le 30 ]; then
    exit 0
fi

# --- 找最近修改的 active plan（plan 文件 gitignored，不能依赖 git status）---
# 按 mtime 取 active/ 下最近改过的 plan；排除 README / _template
plan_dir="${CLAUDE_PROJECT_DIR:-.}/.ai/superpowers/plans/active"
plan_candidate=""
if [ -d "$plan_dir" ]; then
    plan_candidate=$(ls -t "$plan_dir"/*.md 2>/dev/null | grep -vE '/(README|_template)\.md$' | head -1)
fi

# 无活跃 plan + 非琐碎 diff → Iron Law #2 要求建 plan；与 plan 缺 Validation 走同一 block 分支
if [ -z "$plan_candidate" ] || [ ! -f "$plan_candidate" ]; then
    FILE_COUNT="$file_count" DIFF_LINES="$diff_lines" python3 <<'PY'
import json
import os

reason = f"""[Stop BLOCK] 本轮有非琐碎 diff（{os.environ["FILE_COUNT"]} 文件 / {os.environ["DIFF_LINES"]} diff 行）但 .ai/superpowers/plans/active/ 下无活跃 plan。Iron Law #2：非琐碎工作必须起 plan。使用 writing-plans skill 生成 plan，并保存到 .ai/superpowers/plans/active/<YYYY-MM>-<slug>.md；若实际是纯形式改动（typo / 格式 / 路径）请缩小 diff；否则补 plan 再收尾。"""
print(json.dumps({"decision": "block", "reason": reason}))
PY
    exit 0
fi

# --- Nudge 计数：单 session 累计 block 上限 CC_STOP_MAX 次 ---
STATE_DIR="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/state"
mkdir -p "$STATE_DIR" 2>/dev/null || true
counter_file="$STATE_DIR/stop-${session_id}.count"
max_nudges="$max_nudges_config"

count=0
[ -f "$counter_file" ] && count=$(cat "$counter_file" 2>/dev/null || echo 0)

# --- 判定触发原因：缺 Validation 段 / 段内无内容 或 有未勾 checkbox ---
block_reason=""
validation_state=$(python3 - "$plan_candidate" <<'PY' 2>/dev/null
import re, sys
path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
except Exception:
    print("missing")
    sys.exit(0)

heading_re = re.compile(r'^#{2,4} (?:Round \d+ )?Validation\s*$', re.MULTILINE)
match = heading_re.search(text)
if not match:
    print("missing")
    sys.exit(0)

tail = text[match.end():]
next_heading = re.search(r'^#{1,6} ', tail, re.MULTILINE)
body = tail[:next_heading.start()] if next_heading else tail
if any(line.strip() for line in body.splitlines()):
    print("ok")
else:
    print("empty")
PY
) || validation_state="missing"
if [ "$validation_state" = "missing" ]; then
    block_reason="活跃 plan $plan_candidate 缺 '## Validation' 段（Iron Law #3）。补完实际验证命令与结果，或在 Decisions 段显式记 '未完结待续，理由 ...'。"
elif [ "$validation_state" = "empty" ]; then
    block_reason="活跃 plan $plan_candidate 的 '## Validation' 段为空（Iron Law #3）。在该段落贴出当轮实际运行的命令与输出摘要，或在 Decisions 段显式记 '未完结待续，理由 ...'。"
elif grep -qE '^\s*- \[ \]' "$plan_candidate" 2>/dev/null; then
    unchecked=$(grep -cE '^\s*- \[ \]' "$plan_candidate" 2>/dev/null || echo 0)
    block_reason="活跃 plan $plan_candidate 仍有 $unchecked 个未勾任务（- [ ]）+ 本轮非琐碎 diff（$file_count 文件）。Iron Law #5：计划就绪无阻塞时一轮内跑完剩余步骤。"
fi

# 无阻塞原因 → 放行
[ -z "$block_reason" ] && { rm -f "$counter_file"; exit 0; }

# 达到 nudge 上限 → 放行（防真死锁）
count=$((count + 1))
echo "$count" > "$counter_file"
if [ "$max_nudges" -gt 0 ] && [ "$count" -gt "$max_nudges" ]; then
    rm -f "$counter_file"
    exit 0
fi

# --- 输出 JSON block + Blocker Decision Framework ---
# 官方协议：exit 0 + stdout JSON `{"decision":"block","reason":"..."}` 让 Claude 继续
BLOCK_COUNT="$count" \
BLOCK_MAX="$max_nudges" \
BLOCK_REASON="$block_reason" \
python3 <<'PY'
import json
import os

reason = f"""[Stop BLOCK nudge {os.environ["BLOCK_COUNT"]}/{os.environ["BLOCK_MAX"]}] {os.environ["BLOCK_REASON"]}

Blocker Decision Framework（business-as-usual；不允许停下等用户催）：
  L1 能自解 → 解决（读代码 / 读文档 / 修 typo / 补 Validation 段）
  L2 可 workaround 且结果等价 → 做，并在 plan Decisions 记一行
  L3 真 blocked → plan Decisions 加 '未完结待续，理由：<具体 + 用户需做什么>' + 把剩余任务改 '- [x] ~~(moved to follow-up)~~' 后移下一个任务
不允许：brute-force 重试 / 禁用安全检查 / 不可逆操作（git push / reset --hard / 删分支 / 改 CI-CD / 对外通讯）未经用户明确授权 / 凭据猜测。
只有命中 workflow skill 的 '不可逆动作闸门' 清单时才允许停下等用户。"""
print(json.dumps({"decision": "block", "reason": reason}))
PY

exit 0
