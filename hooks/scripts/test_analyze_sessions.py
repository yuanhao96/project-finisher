#!/usr/bin/env python3
"""
Tests for analyze-sessions.py — validates all 7 behavioral dimensions.

Run: python3 test_analyze_sessions.py
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Import the module under test
script_dir = str(Path(__file__).resolve().parent)
sys.path.insert(0, script_dir)

# The module is named with a hyphen in the filename, use importlib
import importlib.util
spec = importlib.util.spec_from_file_location("analyze_sessions", os.path.join(script_dir, "analyze-sessions.py"))
analyzer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyzer)


def make_entry(tool, ts_offset_sec=0, session="test-session-1", edit_size=None, bash_ok=None):
    """Create a synthetic log entry."""
    ts = datetime(2026, 3, 11, 12, 0, 0) + timedelta(seconds=ts_offset_sec)
    entry = {
        "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool": tool,
        "project": "/test/project",
        "session": session,
    }
    if edit_size is not None:
        entry["edit_size"] = edit_size
    if bash_ok is not None:
        entry["bash_ok"] = bash_ok
    return entry


def test_classify_pacing():
    """Test pacing classification."""
    # Fast: many tools in short time
    entries = [make_entry("Edit", i * 5) for i in range(20)]  # 20 tools in ~95 sec
    stats = analyzer.analyze_session("fast-session", entries)
    assert analyzer.classify_pacing(stats) == "fast", f"Expected fast, got {analyzer.classify_pacing(stats)}"

    # Deliberate: few tools over long time
    entries = [make_entry("Read", i * 300) for i in range(5)]  # 5 tools over 20 min
    stats = analyzer.analyze_session("deliberate-session", entries)
    assert analyzer.classify_pacing(stats) == "deliberate", f"Expected deliberate, got {analyzer.classify_pacing(stats)}"

    print("  PASS: classify_pacing")


def test_classify_depth():
    """Test depth classification."""
    # Shallow: mostly action tools
    entries = [
        make_entry("Edit", 0), make_entry("Edit", 1), make_entry("Bash", 2),
        make_entry("Edit", 3), make_entry("Bash", 4), make_entry("Write", 5),
        make_entry("Edit", 6), make_entry("Bash", 7), make_entry("Edit", 8),
        make_entry("Edit", 9),
    ]
    stats = analyzer.analyze_session("shallow-session", entries)
    assert analyzer.classify_depth(stats) == "shallow", f"Expected shallow, got {analyzer.classify_depth(stats)}"

    # Deep: Agent usage present
    entries = [
        make_entry("Read", 0), make_entry("Agent", 1), make_entry("Read", 2),
        make_entry("Grep", 3), make_entry("Read", 4),
    ]
    stats = analyzer.analyze_session("deep-session", entries)
    assert analyzer.classify_depth(stats) == "deep", f"Expected deep, got {analyzer.classify_depth(stats)}"

    print("  PASS: classify_depth")


def test_classify_workflow():
    """Test workflow classification."""
    # Pure execution: edits without agents
    entries = [make_entry("Edit", i) for i in range(10)]
    stats = analyzer.analyze_session("exec-session", entries)
    assert analyzer.classify_workflow(stats) == "pure execution"

    # Diagnostic: reads without edits
    entries = [make_entry("Read", i) for i in range(10)]
    stats = analyzer.analyze_session("diag-session", entries)
    assert analyzer.classify_workflow(stats) == "diagnostic"

    # Quick interaction
    entries = [make_entry("Read", 0), make_entry("Edit", 1)]
    stats = analyzer.analyze_session("quick-session", entries)
    assert analyzer.classify_workflow(stats) == "quick interaction"

    print("  PASS: classify_workflow")


def test_classify_edit_size():
    """Test edit size classification."""
    # Incremental: small edits
    entries = [
        make_entry("Edit", 0, edit_size=10),
        make_entry("Edit", 1, edit_size=20),
        make_entry("Edit", 2, edit_size=5),
        make_entry("Edit", 3, edit_size=30),
        make_entry("Edit", 4, edit_size=15),
    ]
    stats = analyzer.analyze_session("small-edit-session", entries)
    result = analyzer.classify_edit_size(stats)
    assert result == "incremental", f"Expected incremental, got {result}"

    # Large rewrite: big edits
    entries = [
        make_entry("Write", 0, edit_size=1000),
        make_entry("Write", 1, edit_size=800),
        make_entry("Edit", 2, edit_size=600),
        make_entry("Write", 3, edit_size=1200),
        make_entry("Edit", 4, edit_size=700),
    ]
    stats = analyzer.analyze_session("large-edit-session", entries)
    result = analyzer.classify_edit_size(stats)
    assert result == "large-rewrite", f"Expected large-rewrite, got {result}"

    # Mixed: no edit_size data (backwards compatibility)
    entries = [make_entry("Edit", 0), make_entry("Edit", 1)]
    stats = analyzer.analyze_session("no-size-session", entries)
    result = analyzer.classify_edit_size(stats)
    assert result == "mixed", f"Expected mixed (no data), got {result}"

    print("  PASS: classify_edit_size")


def test_classify_error_recovery():
    """Test error recovery classification."""
    # Retry: bash fails then bash again
    entries = [
        make_entry("Bash", 0, bash_ok=False),
        make_entry("Bash", 1, bash_ok=True),
        make_entry("Bash", 2, bash_ok=False),
        make_entry("Bash", 3, bash_ok=True),
        make_entry("Bash", 4, bash_ok=False),
        make_entry("Bash", 5, bash_ok=True),
    ]
    stats = analyzer.analyze_session("retry-session", entries)
    result = analyzer.classify_error_recovery(stats)
    assert result == "retry", f"Expected retry, got {result}"

    # Investigate: bash fails then read/grep
    entries = [
        make_entry("Bash", 0, bash_ok=False),
        make_entry("Read", 1),
        make_entry("Bash", 2, bash_ok=False),
        make_entry("Grep", 3),
        make_entry("Bash", 4, bash_ok=False),
        make_entry("Read", 5),
    ]
    stats = analyzer.analyze_session("investigate-session", entries)
    result = analyzer.classify_error_recovery(stats)
    assert result == "investigate", f"Expected investigate, got {result}"

    # No errors: should be mixed
    entries = [make_entry("Bash", 0, bash_ok=True), make_entry("Bash", 1, bash_ok=True)]
    stats = analyzer.analyze_session("no-error-session", entries)
    result = analyzer.classify_error_recovery(stats)
    assert result == "mixed", f"Expected mixed (no errors), got {result}"

    print("  PASS: classify_error_recovery")


def test_classify_interaction_patterns():
    """Test interaction pattern classification."""
    # Cautious: high read:edit ratio
    entries = [
        make_entry("Read", 0), make_entry("Read", 1), make_entry("Read", 2),
        make_entry("Edit", 3),
        make_entry("Read", 4), make_entry("Read", 5),
        make_entry("Edit", 6),
    ]
    stats = analyzer.analyze_session("cautious-session", entries)
    result = analyzer.classify_interaction_patterns(stats)
    assert result == "cautious", f"Expected cautious, got {result}"

    # Direct: low read:edit ratio
    entries = [
        make_entry("Edit", 0), make_entry("Edit", 1), make_entry("Edit", 2),
        make_entry("Edit", 3), make_entry("Edit", 4),
        make_entry("Read", 5),
    ]
    stats = analyzer.analyze_session("direct-session", entries)
    result = analyzer.classify_interaction_patterns(stats)
    assert result == "direct", f"Expected direct, got {result}"

    print("  PASS: classify_interaction_patterns")


def test_confidence_counter():
    """Test confidence counter agree/disagree logic."""
    # Agree: same style increments confidence
    style, conf = analyzer.update_confidence("fast", 3, "fast")
    assert style == "fast" and conf == 4

    # Disagree: decrements confidence
    style, conf = analyzer.update_confidence("fast", 3, "deliberate")
    assert style == "fast" and conf == 2

    # Flip: confidence reaches 0 then flips
    style, conf = analyzer.update_confidence("fast", 1, "deliberate")
    assert style == "deliberate" and conf == 1

    print("  PASS: confidence_counter")


def test_backwards_compatibility():
    """Test that old entries without enriched fields work correctly."""
    # Old-style entries (no edit_size, no bash_ok)
    entries = [
        make_entry("Read", 0),
        make_entry("Edit", 5),
        make_entry("Bash", 10),
        make_entry("Read", 15),
        make_entry("Edit", 20),
        make_entry("Bash", 25),
    ]
    stats = analyzer.analyze_session("old-style", entries)

    # Should still classify pacing/depth/workflow
    assert analyzer.classify_pacing(stats) in ("fast", "deliberate", "mixed")
    assert analyzer.classify_depth(stats) in ("shallow", "deep", "mixed")
    assert analyzer.classify_workflow(stats) in ("pure execution", "diagnostic", "brainstorm+execute", "quick interaction", "mixed")

    # New dimensions should default to mixed (no enriched data)
    assert analyzer.classify_edit_size(stats) == "mixed"
    assert analyzer.classify_error_recovery(stats) == "mixed"
    # Interaction patterns use tool counts, not enriched fields
    assert analyzer.classify_interaction_patterns(stats) in ("cautious", "direct", "mixed")

    print("  PASS: backwards_compatibility")


def test_tool_pairs():
    """Test tool pair frequency computation."""
    entries = [
        make_entry("Read", 0),
        make_entry("Edit", 1),
        make_entry("Read", 2),
        make_entry("Edit", 3),
    ]
    stats = analyzer.analyze_session("pair-session", entries)
    pairs = stats["tool_pairs"]
    assert pairs.get("Read→Edit", 0) == 2, f"Expected 2 Read→Edit pairs, got {pairs.get('Read→Edit', 0)}"
    assert pairs.get("Edit→Read", 0) == 1, f"Expected 1 Edit→Read pair, got {pairs.get('Edit→Read', 0)}"

    print("  PASS: tool_pairs")


def main():
    print("Running analyze-sessions.py tests...\n")

    tests = [
        test_classify_pacing,
        test_classify_depth,
        test_classify_workflow,
        test_classify_edit_size,
        test_classify_error_recovery,
        test_classify_interaction_patterns,
        test_confidence_counter,
        test_backwards_compatibility,
        test_tool_pairs,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {test.__name__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed out of {len(tests)} tests")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
