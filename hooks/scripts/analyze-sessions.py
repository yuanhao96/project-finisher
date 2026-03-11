#!/usr/bin/env python3
"""
Fully deterministic session analyzer for project-finisher evolve system.

Reads behavior_log.jsonl, identifies sessions not yet reflected in
workflow_preferences.md, computes quantitative stats AND qualitative
classifications (pacing, depth, workflow), and updates the preferences
file completely — no LLM layer needed.

Exit codes:
  0 - analysis completed, workflow_preferences.md updated
  1 - no new sessions to analyze (or error)
"""

import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

DATA_DIR = Path.home() / ".claude" / "project-finisher-data"
LOG_FILE = DATA_DIR / "behavior_log.jsonl"
PREFS_FILE = DATA_DIR / "workflow_preferences.md"
PENDING_FILE = DATA_DIR / "pending_session_analysis.json"

# --- Heuristic thresholds ---
FAST_TOOLS_PER_MIN = 3.0
DELIBERATE_TOOLS_PER_MIN = 1.0
FAST_MAX_DURATION_MIN = 3.0
DELIBERATE_MIN_DURATION_MIN = 10.0
ACTION_RATIO_SHALLOW = 0.7
EXPLORE_RATIO_DEEP = 0.7
QUICK_INTERACTION_THRESHOLD = 5

# --- Templated signals ---
PACING_SIGNALS = {
    "fast": "High tool density ({rate:.1f}/min avg). Sessions typically short and action-oriented.",
    "deliberate": "Low tool density ({rate:.1f}/min avg). Extended sessions with thinking pauses.",
    "mixed": "Variable pacing across sessions ({rate:.1f}/min avg).",
}
DEPTH_SIGNALS = {
    "shallow": "Action-heavy sessions (Edit/Write/Bash dominate at {action_pct:.0f}%). Minimal exploration phases.",
    "deep": "Exploration-heavy sessions (Read/Grep/Glob/Agent at {explore_pct:.0f}%). Investigative approach.",
    "mixed": "Balanced action ({action_pct:.0f}%) and exploration ({explore_pct:.0f}%) across sessions.",
}
PACING_ADAPTATIONS = {
    "fast": "Limit brainstorming to 2 rounds max. Skip confirmation prompts. Compress Review phase to bullet points. Prefer action over discussion.",
    "deliberate": "Run full multi-round brainstorming. Include tradeoff discussions. Provide detailed review summaries.",
    "mixed": "Default behavior — adapt per-session based on context.",
}
DEPTH_ADAPTATIONS = {
    "shallow": "Default to code-only responses during execution. Save explanations for brainstorming phases or when explicitly asked.",
    "deep": "Include rationale for decisions. Discuss alternatives considered. Reference prior lessons explicitly.",
    "mixed": "Default behavior — provide moderate explanations.",
}


def read_log_entries():
    """Read all entries from behavior_log.jsonl."""
    if not LOG_FILE.exists():
        return []
    entries = []
    for line in LOG_FILE.read_text().strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def get_known_session_ids(prefs_text):
    """Extract session IDs from the preferences file metadata comment."""
    match = re.search(r'<!--\s*analyzed_sessions:\s*(.+?)\s*-->', prefs_text)
    if match:
        return set(match.group(1).split(","))
    return set()


def group_by_session(entries):
    """Group log entries by session ID."""
    sessions = defaultdict(list)
    for entry in entries:
        sid = entry.get("session", "unknown")
        sessions[sid].append(entry)
    for sid in sessions:
        sessions[sid].sort(key=lambda e: e.get("ts", ""))
    return dict(sessions)


def analyze_session(session_id, entries):
    """Compute stats for a single session."""
    tool_counts = Counter()
    for entry in entries:
        tool_counts[entry.get("tool", "unknown")] += 1

    timestamps = [e.get("ts", "") for e in entries if e.get("ts")]
    duration_min = None
    if len(timestamps) >= 2:
        try:
            t_start = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
            t_end = datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00"))
            duration_min = round((t_end - t_start).total_seconds() / 60, 1)
        except (ValueError, TypeError):
            pass

    date_str = timestamps[0][:10] if timestamps else ""
    top_tools = tool_counts.most_common(5)
    total_tools = sum(tool_counts.values())

    return {
        "session_id": session_id,
        "date": date_str,
        "total_tool_calls": total_tools,
        "duration_min": duration_min,
        "tool_counts": dict(tool_counts),
        "top_tools": [{"tool": t, "count": c} for t, c in top_tools],
        "agent_count": tool_counts.get("Agent", 0),
        "edit_count": tool_counts.get("Edit", 0),
        "write_count": tool_counts.get("Write", 0),
        "read_count": tool_counts.get("Read", 0),
        "bash_count": tool_counts.get("Bash", 0),
        "grep_count": tool_counts.get("Grep", 0),
        "glob_count": tool_counts.get("Glob", 0),
        "skill_count": tool_counts.get("Skill", 0),
    }


# =========================================================
# Qualitative classification heuristics
# =========================================================

def classify_pacing(stats):
    """Classify session pacing as fast/deliberate/mixed."""
    total = stats["total_tool_calls"]
    dur = stats["duration_min"]

    if dur is None or dur == 0:
        # Can't compute rate — short session, assume fast
        return "fast"

    rate = total / dur

    if rate >= FAST_TOOLS_PER_MIN or dur < FAST_MAX_DURATION_MIN:
        return "fast"
    if rate < DELIBERATE_TOOLS_PER_MIN and dur > DELIBERATE_MIN_DURATION_MIN:
        return "deliberate"
    return "mixed"


def classify_depth(stats):
    """Classify session depth as shallow/deep/mixed."""
    total = stats["total_tool_calls"]
    if total == 0:
        return "mixed"

    action = stats["edit_count"] + stats["write_count"] + stats["bash_count"]
    explore = stats["read_count"] + stats["grep_count"] + stats["glob_count"] + stats["agent_count"]
    action_ratio = action / total
    explore_ratio = explore / total

    if action_ratio > ACTION_RATIO_SHALLOW and stats["agent_count"] == 0:
        return "shallow"
    if stats["agent_count"] > 0 or explore_ratio > EXPLORE_RATIO_DEEP:
        return "deep"
    return "mixed"


def classify_workflow(stats):
    """Classify session workflow phase."""
    total = stats["total_tool_calls"]
    has_edits = (stats["edit_count"] + stats["write_count"]) > 0
    has_agent = stats["agent_count"] > 0

    if total < QUICK_INTERACTION_THRESHOLD:
        return "quick interaction"
    if not has_edits:
        return "diagnostic"
    if has_edits and has_agent:
        return "brainstorm+execute"
    if has_edits and not has_agent:
        return "pure execution"
    return "mixed"


def classify_session(stats):
    """Full qualitative classification of a session."""
    return {
        "pacing": classify_pacing(stats),
        "depth": classify_depth(stats),
        "workflow": classify_workflow(stats),
    }


# =========================================================
# Confidence counter logic
# =========================================================

def update_confidence(current_style, current_conf, observed_style):
    """Update style and confidence using agree/disagree counter."""
    if observed_style == current_style:
        return current_style, current_conf + 1
    else:
        new_conf = current_conf - 1
        if new_conf <= 0:
            return observed_style, 1  # flip
        return current_style, new_conf


# =========================================================
# Parse current preferences
# =========================================================

def parse_prefs(prefs_text):
    """Extract current style and confidence values from prefs markdown."""
    result = {}
    for dimension in ["Pacing", "Depth"]:
        style_match = re.search(
            rf'## {dimension}\s*\n.*?\*\*Style\*\*:\s*(\w+)',
            prefs_text, re.DOTALL
        )
        conf_match = re.search(
            rf'## {dimension}\s*\n.*?\*\*Confidence\*\*:\s*(\d+)',
            prefs_text, re.DOTALL
        )
        result[dimension.lower()] = {
            "style": style_match.group(1) if style_match else "mixed",
            "confidence": int(conf_match.group(1)) if conf_match else 0,
        }

    # Workflow ordering confidence
    wf_conf_match = re.search(r'## Workflow Ordering.*?\*\*Confidence\*\*:\s*(\d+)', prefs_text, re.DOTALL)
    wf_seq_match = re.search(r'\*\*Preferred sequence\*\*:\s*(.+)', prefs_text)
    result["workflow"] = {
        "style": wf_seq_match.group(1).strip() if wf_seq_match else "mixed",
        "confidence": int(wf_conf_match.group(1)) if wf_conf_match else 0,
    }

    # Tool preferences
    tool_conf_match = re.search(r'## Tool Preferences.*?\*\*Confidence\*\*:\s*(\d+)', prefs_text, re.DOTALL)
    agent_match = re.search(r'\*\*Agent vs direct\*\*:\s*(\S+)', prefs_text)
    edit_match = re.search(r'\*\*Edit vs Write\*\*:\s*(\S+)', prefs_text)
    result["tools"] = {
        "agent_pref": agent_match.group(1) if agent_match else "mixed",
        "edit_pref": edit_match.group(1) if edit_match else "mixed",
        "confidence": int(tool_conf_match.group(1)) if tool_conf_match else 0,
    }

    return result


# =========================================================
# Compute aggregate stats for signals text
# =========================================================

def compute_aggregate_signals(all_session_stats):
    """Compute aggregate metrics for templated signals text."""
    total_tools = sum(s["total_tool_calls"] for s in all_session_stats)
    total_duration = sum(s["duration_min"] or 0 for s in all_session_stats)
    avg_rate = total_tools / total_duration if total_duration > 0 else 0

    total_action = sum(s["edit_count"] + s["write_count"] + s["bash_count"] for s in all_session_stats)
    total_explore = sum(s["read_count"] + s["grep_count"] + s["glob_count"] + s["agent_count"] for s in all_session_stats)
    action_pct = (total_action / total_tools * 100) if total_tools > 0 else 0
    explore_pct = (total_explore / total_tools * 100) if total_tools > 0 else 0

    total_agents = sum(s["agent_count"] for s in all_session_stats)
    total_edits = sum(s["edit_count"] for s in all_session_stats)
    total_writes = sum(s["write_count"] for s in all_session_stats)

    return {
        "rate": avg_rate,
        "action_pct": action_pct,
        "explore_pct": explore_pct,
        "total_agents": total_agents,
        "total_edits": total_edits,
        "total_writes": total_writes,
    }


# =========================================================
# Derive workflow ordering summary
# =========================================================

def derive_workflow_ordering(all_classifications):
    """Summarize workflow ordering from all session classifications."""
    wf_counts = Counter(c["workflow"] for c in all_classifications)
    most_common = wf_counts.most_common(1)[0][0] if wf_counts else "mixed"

    # Determine preferred sequence
    has_brainstorm = wf_counts.get("brainstorm+execute", 0) > 0
    has_pure_exec = wf_counts.get("pure execution", 0) > 0

    if has_brainstorm and has_pure_exec:
        preferred = "brainstorm → execute (light planning inline)"
    elif has_pure_exec and not has_brainstorm:
        preferred = "execute directly (skip brainstorm)"
    elif has_brainstorm:
        preferred = "brainstorm → execute"
    else:
        preferred = "mixed"

    # Determine skipped phases
    skipped = []
    if wf_counts.get("brainstorm+execute", 0) == 0 and len(all_classifications) >= 3:
        skipped.append("brainstorm")
    # If no sessions have Agent usage, formal planning is likely skipped
    skipped.append("formal plan phase")
    skipped.append("detailed review")

    return preferred, skipped


# =========================================================
# Derive tool preferences
# =========================================================

def derive_tool_prefs(all_session_stats):
    """Derive agent vs direct and edit vs write preferences."""
    total_agents = sum(s["agent_count"] for s in all_session_stats)
    total_direct = sum(
        s["read_count"] + s["grep_count"] + s["glob_count"] +
        s["edit_count"] + s["write_count"] + s["bash_count"]
        for s in all_session_stats
    )
    total_edits = sum(s["edit_count"] for s in all_session_stats)
    total_writes = sum(s["write_count"] for s in all_session_stats)

    if total_agents == 0:
        agent_pref = "prefer-direct"
    elif total_agents > total_direct * 0.3:
        agent_pref = "prefer-agents"
    else:
        agent_pref = "mixed"

    if total_writes == 0 or (total_edits > 0 and total_edits > total_writes * 3):
        edit_pref = "prefer-edit"
    elif total_edits == 0:
        edit_pref = "prefer-write"
    else:
        edit_pref = "mixed"

    return agent_pref, edit_pref


# =========================================================
# Generate the full preferences markdown
# =========================================================

def generate_prefs_markdown(
    pacing_style, pacing_conf,
    depth_style, depth_conf,
    wf_preferred, wf_skipped, wf_conf,
    agent_pref, edit_pref, tool_conf,
    all_tool_counts, total_sessions,
    session_rows, all_session_ids,
    aggregate_signals,
):
    """Generate the complete workflow_preferences.md content."""
    today = datetime.now().strftime("%Y-%m-%d")
    top5 = all_tool_counts.most_common(5)
    top5_str = ", ".join(f"{t}({c})" for t, c in top5)
    skipped_str = ", ".join(wf_skipped) if wf_skipped else "none"

    pacing_sig = PACING_SIGNALS[pacing_style].format(**aggregate_signals)
    depth_sig = DEPTH_SIGNALS[depth_style].format(**aggregate_signals)
    pacing_adapt = PACING_ADAPTATIONS[pacing_style]
    depth_adapt = DEPTH_ADAPTATIONS[depth_style]

    # Workflow adaptation
    if "brainstorm" in skipped_str:
        wf_adapt = "Skip brainstorm phase. Jump directly to execution with inline planning."
    elif wf_preferred.startswith("brainstorm"):
        wf_adapt = "Allow brainstorm-to-execute shortcut for straightforward milestones. Keep formal planning for complex/risky milestones."
    else:
        wf_adapt = "Default workflow — adapt per milestone complexity."

    lines = [
        "# Workflow Preferences",
        "",
        f"_Auto-generated by project-finisher evolve skill. Last updated: {today}_",
        f"_Total sessions observed: {total_sessions}_",
        "",
        "## Pacing",
        "",
        f"- **Style**: {pacing_style}",
        f"- **Confidence**: {pacing_conf}",
        f"- **Signals**: {pacing_sig}",
        f"- **Adaptation**: {pacing_adapt}",
        "",
        "## Depth",
        "",
        f"- **Style**: {depth_style}",
        f"- **Confidence**: {depth_conf}",
        f"- **Signals**: {depth_sig}",
        f"- **Adaptation**: {depth_adapt}",
        "",
        "## Workflow Ordering",
        "",
        f"- **Preferred sequence**: {wf_preferred}",
        f"- **Phases typically skipped**: {skipped_str}",
        f"- **Confidence**: {wf_conf}",
        f"- **Adaptation**: {wf_adapt}",
        "",
        "## Tool Preferences",
        "",
        f"- **Agent vs direct**: {agent_pref}",
        f"- **Edit vs Write**: {edit_pref}",
        f"- **Top 5 tools by frequency**: {top5_str}",
        f"- **Confidence**: {tool_conf}",
        f"- **Adaptation**: Use direct tools over Agent subagents. Heavy Bash for shell operations. Edit for modifications, Write only for new files. Read extensively before editing."
        if agent_pref == "prefer-direct"
        else f"- **Adaptation**: Delegate research to Agent subagents. Use direct tools for targeted operations.",
        "",
        "## Session Log",
        "",
        "| Date | Pacing | Depth | Workflow | Notes |",
        "|------|--------|-------|----------|-------|",
    ]

    for row in session_rows:
        lines.append(row)

    lines.append("")
    ids_str = ",".join(sorted(all_session_ids))
    lines.append(f"<!-- analyzed_sessions: {ids_str} -->")

    return "\n".join(lines) + "\n"


# =========================================================
# Parse existing session rows from prefs
# =========================================================

def parse_existing_session_rows(prefs_text):
    """Extract existing session log rows from prefs markdown."""
    rows = []
    in_table = False
    for line in prefs_text.splitlines():
        if line.startswith("| Date "):
            in_table = True
            continue
        if line.startswith("|------"):
            continue
        if in_table and line.startswith("|"):
            rows.append(line)
        elif in_table and not line.startswith("|"):
            break
    return rows


# =========================================================
# Main
# =========================================================

def main():
    entries = read_log_entries()
    if not entries:
        sys.exit(1)

    # Read current preferences
    prefs_text = PREFS_FILE.read_text() if PREFS_FILE.exists() else ""

    # Get already-analyzed session IDs
    known_ids = get_known_session_ids(prefs_text)

    # Group entries by session
    sessions = group_by_session(entries)

    # Find new sessions
    new_session_ids = [sid for sid in sessions if sid not in known_ids]
    if not new_session_ids:
        # Clean up any stale pending file
        if PENDING_FILE.exists():
            PENDING_FILE.unlink()
        sys.exit(1)

    # Analyze new sessions
    new_stats = []
    new_classifications = []
    for sid in new_session_ids:
        stats = analyze_session(sid, sessions[sid])
        classification = classify_session(stats)
        new_stats.append(stats)
        new_classifications.append(classification)

    # Parse current preferences for confidence updates
    current_prefs = parse_prefs(prefs_text) if prefs_text else {
        "pacing": {"style": "mixed", "confidence": 0},
        "depth": {"style": "mixed", "confidence": 0},
        "workflow": {"style": "mixed", "confidence": 0},
        "tools": {"agent_pref": "mixed", "edit_pref": "mixed", "confidence": 0},
    }

    # Apply confidence counter for each new session
    pacing_style = current_prefs["pacing"]["style"]
    pacing_conf = current_prefs["pacing"]["confidence"]
    depth_style = current_prefs["depth"]["style"]
    depth_conf = current_prefs["depth"]["confidence"]

    for cl in new_classifications:
        pacing_style, pacing_conf = update_confidence(pacing_style, pacing_conf, cl["pacing"])
        depth_style, depth_conf = update_confidence(depth_style, depth_conf, cl["depth"])

    # Compute cumulative tool counts
    all_tool_counts = Counter()
    top_match = re.search(r'\*\*Top 5 tools by frequency\*\*:\s*(.+)', prefs_text)
    if top_match:
        for item in re.findall(r'(\w+)\((\d+)\)', top_match.group(1)):
            all_tool_counts[item[0]] += int(item[1])
    for stats in new_stats:
        for tool, count in stats["tool_counts"].items():
            all_tool_counts[tool] += count

    # Total sessions
    current_count_match = re.search(r'Total sessions observed:\s*(\d+)', prefs_text)
    old_count = int(current_count_match.group(1)) if current_count_match else 0
    total_sessions = old_count + len(new_stats)

    # Build session rows (keep existing + add new)
    existing_rows = parse_existing_session_rows(prefs_text)
    new_rows = []
    for stats, cl in zip(new_stats, new_classifications):
        date = stats["date"]
        duration = f"~{stats['duration_min']}min" if stats["duration_min"] else "unknown"
        top3 = "+".join(t["tool"] for t in stats["top_tools"][:3])
        row = f"| {date} | {cl['pacing']} | {cl['depth']} | {cl['workflow']} | Session {stats['session_id'][:8]}. {stats['total_tool_calls']} tool calls, {duration}. Top: {top3}. |"
        new_rows.append(row)
    all_rows = existing_rows + new_rows

    # All session IDs
    all_session_ids = known_ids | {s["session_id"] for s in new_stats}

    # Derive workflow ordering from all session classifications
    # Re-classify existing rows from the table for a full picture
    all_classifications_for_wf = []
    for row in existing_rows:
        parts = [p.strip() for p in row.split("|") if p.strip()]
        if len(parts) >= 4:
            all_classifications_for_wf.append({"workflow": parts[3]})
    all_classifications_for_wf.extend(new_classifications)
    wf_preferred, wf_skipped = derive_workflow_ordering(all_classifications_for_wf)

    # Workflow confidence: simple count of sessions with same primary workflow
    wf_counts = Counter(c["workflow"] for c in all_classifications_for_wf)
    wf_conf = max(wf_counts.values()) if wf_counts else 0

    # Tool preferences
    # We need stats for all sessions, but we only have detailed stats for
    # sessions in the current log. Use cumulative tool counts as proxy.
    agent_pref, edit_pref = derive_tool_prefs(new_stats)
    # Override with cumulative if we have data
    total_agents_cum = all_tool_counts.get("Agent", 0)
    total_direct_cum = sum(all_tool_counts.get(t, 0) for t in ["Read", "Grep", "Glob", "Edit", "Write", "Bash"])
    total_edits_cum = all_tool_counts.get("Edit", 0)
    total_writes_cum = all_tool_counts.get("Write", 0)
    if total_agents_cum == 0:
        agent_pref = "prefer-direct"
    elif total_agents_cum > total_direct_cum * 0.3:
        agent_pref = "prefer-agents"
    else:
        agent_pref = "mixed"
    if total_writes_cum == 0 or (total_edits_cum > 0 and total_edits_cum > total_writes_cum * 3):
        edit_pref = "prefer-edit"
    elif total_edits_cum == 0:
        edit_pref = "prefer-write"
    else:
        edit_pref = "mixed"

    tool_conf = current_prefs["tools"]["confidence"] + len(new_stats)

    # Aggregate signals for templated text
    # Use new sessions for rate calculation (we have timestamps)
    agg = compute_aggregate_signals(new_stats)

    # Generate full preferences markdown
    prefs_md = generate_prefs_markdown(
        pacing_style, pacing_conf,
        depth_style, depth_conf,
        wf_preferred, wf_skipped, wf_conf,
        agent_pref, edit_pref, tool_conf,
        all_tool_counts, total_sessions,
        all_rows, all_session_ids,
        agg,
    )

    PREFS_FILE.write_text(prefs_md)

    # Clean up any stale pending file — no longer needed
    if PENDING_FILE.exists():
        PENDING_FILE.unlink()

    print(f"workflow_preferences.md updated: {len(new_stats)} new session(s) fully analyzed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
