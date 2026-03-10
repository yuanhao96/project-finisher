#!/usr/bin/env python3
"""
Deterministic session analyzer for project-finisher evolve system.

Reads behavior_log.jsonl, identifies sessions not yet reflected in
workflow_preferences.md, computes quantitative stats, and:
  1. Updates workflow_preferences.md with new session count + tool stats
  2. Writes pending_session_analysis.json for LLM qualitative review

Exit codes:
  0 - analysis completed, pending_session_analysis.json written
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


def get_known_sessions(prefs_text):
    """Extract session IDs already recorded in the session log table."""
    # We track by session date+notes combo, but more reliably by counting
    # the number of session rows in the table
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
            in_table = False
    return len(rows)


def get_known_session_ids(prefs_text):
    """Extract session IDs from the preferences file if stored."""
    # Look for session IDs in a metadata comment
    match = re.search(r'<!--\s*analyzed_sessions:\s*(.+?)\s*-->', prefs_text)
    if match:
        return set(match.group(1).split(","))
    return set()


def group_by_session(entries):
    """Group log entries by session ID."""
    sessions = defaultdict(list)
    for entry in entries:
        sid = entry.get("session", "unknown")
        sessions[sid] = sessions.get(sid, [])
        sessions[sid].append(entry)
    # Sort entries within each session by timestamp
    for sid in sessions:
        sessions[sid].sort(key=lambda e: e.get("ts", ""))
    return dict(sessions)


def analyze_session(session_id, entries):
    """Compute stats for a single session."""
    tool_counts = Counter()
    for entry in entries:
        tool_counts[entry.get("tool", "unknown")] += 1

    timestamps = [e.get("ts", "") for e in entries if e.get("ts")]
    if len(timestamps) >= 2:
        try:
            t_start = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
            t_end = datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00"))
            duration_min = round((t_end - t_start).total_seconds() / 60, 1)
        except (ValueError, TypeError):
            duration_min = None
    else:
        duration_min = None

    date_str = ""
    if timestamps:
        date_str = timestamps[0][:10]  # YYYY-MM-DD

    # Top tools
    top_tools = tool_counts.most_common(5)

    # Agent vs direct ratio
    agent_count = tool_counts.get("Agent", 0)
    direct_tools = sum(v for k, v in tool_counts.items() if k in ("Read", "Grep", "Glob", "Edit", "Write", "Bash"))
    total_tools = sum(tool_counts.values())

    # Edit vs Write ratio
    edit_count = tool_counts.get("Edit", 0)
    write_count = tool_counts.get("Write", 0)

    return {
        "session_id": session_id,
        "date": date_str,
        "total_tool_calls": total_tools,
        "duration_min": duration_min,
        "tool_counts": dict(tool_counts),
        "top_tools": [{"tool": t, "count": c} for t, c in top_tools],
        "agent_count": agent_count,
        "direct_tool_count": direct_tools,
        "edit_count": edit_count,
        "write_count": write_count,
    }


def update_prefs_quantitative(prefs_text, new_sessions_stats, all_tool_counts):
    """Update quantitative fields in workflow_preferences.md."""
    lines = prefs_text.splitlines()
    result = []

    # Update total sessions count
    current_count_match = re.search(r'Total sessions observed:\s*(\d+)', prefs_text)
    old_count = int(current_count_match.group(1)) if current_count_match else 0
    new_count = old_count + len(new_sessions_stats)

    # Update last-updated date
    today = datetime.now().strftime("%Y-%m-%d")

    for line in lines:
        # Update session count
        if "Total sessions observed:" in line:
            line = f"_Total sessions observed: {new_count}_"
        # Update last-updated date
        if "Last updated:" in line:
            line = re.sub(r'Last updated: \d{4}-\d{2}-\d{2}', f'Last updated: {today}', line)
        result.append(line)

    updated = "\n".join(result)

    # Update top 5 tools line with cumulative stats
    top5 = all_tool_counts.most_common(5)
    top5_str = ", ".join(f"{t}({c})" for t, c in top5)
    updated = re.sub(
        r'\*\*Top 5 tools by frequency\*\*:.*',
        f'**Top 5 tools by frequency**: {top5_str}',
        updated,
    )

    # Append new session rows to the session log table
    new_rows = []
    for stats in new_sessions_stats:
        date = stats["date"]
        duration = f"~{stats['duration_min']}min" if stats["duration_min"] else "unknown"
        top3 = "+".join(t["tool"] for t in stats["top_tools"][:3])
        row = f"| {date} | pending | pending | pending | Auto-detected. {stats['total_tool_calls']} tool calls, {duration}. Top: {top3}. Session: {stats['session_id'][:8]}... |"
        new_rows.append(row)

    if new_rows:
        # Insert before the end of the file, after the last table row
        table_end = updated.rfind("|")
        if table_end != -1:
            # Find the end of that line
            line_end = updated.find("\n", table_end)
            if line_end == -1:
                line_end = len(updated)
            updated = updated[:line_end] + "\n" + "\n".join(new_rows) + updated[line_end:]

    # Add/update the analyzed_sessions metadata comment
    all_session_ids = set()
    existing_ids = get_known_session_ids(prefs_text)
    all_session_ids.update(existing_ids)
    for stats in new_sessions_stats:
        all_session_ids.add(stats["session_id"])

    ids_str = ",".join(sorted(all_session_ids))
    metadata_comment = f"<!-- analyzed_sessions: {ids_str} -->"

    if "<!-- analyzed_sessions:" in updated:
        updated = re.sub(r'<!--\s*analyzed_sessions:.*?-->', metadata_comment, updated)
    else:
        updated += f"\n{metadata_comment}\n"

    return updated


def main():
    entries = read_log_entries()
    if not entries:
        sys.exit(1)

    # Read current preferences
    if PREFS_FILE.exists():
        prefs_text = PREFS_FILE.read_text()
    else:
        prefs_text = ""

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
    for sid in new_session_ids:
        stats = analyze_session(sid, sessions[sid])
        new_stats.append(stats)

    # Compute cumulative tool counts (all sessions, including old)
    all_tool_counts = Counter()
    # Parse existing top tools from prefs
    top_match = re.search(r'\*\*Top 5 tools by frequency\*\*:\s*(.+)', prefs_text)
    if top_match:
        for item in re.findall(r'(\w+)\((\d+)\)', top_match.group(1)):
            all_tool_counts[item[0]] += int(item[1])
    # Add new session counts
    for stats in new_stats:
        for tool, count in stats["tool_counts"].items():
            all_tool_counts[tool] += count

    # Update preferences file (quantitative only)
    if prefs_text:
        updated_prefs = update_prefs_quantitative(prefs_text, new_stats, all_tool_counts)
        PREFS_FILE.write_text(updated_prefs)

    # Write pending analysis for LLM qualitative review
    pending = {
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "new_sessions": new_stats,
        "cumulative_tool_counts": dict(all_tool_counts.most_common()),
        "total_sessions_observed": (
            (int(re.search(r'Total sessions observed:\s*(\d+)', prefs_text).group(1))
             if re.search(r'Total sessions observed:\s*(\d+)', prefs_text) else 0)
            + len(new_stats)
        ),
    }
    PENDING_FILE.write_text(json.dumps(pending, indent=2) + "\n")

    print(f"Analyzed {len(new_stats)} new session(s). Pending qualitative review.", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
