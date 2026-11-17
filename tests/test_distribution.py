import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def run_cmd(cmd):
    print(f"\n[RUN] {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=str(REPO_ROOT))
    if res.stdout:
        print("[STDOUT]", res.stdout.strip())
    if res.stderr:
        print("[STDERR]", res.stderr.strip())
    return res.returncode, res.stdout, res.stderr

def main():
    print("==================================================")
    print("🧪 BEGINNING AUTOMATED SKILL DISTRIBUTION TEST SUITE")
    print("==================================================")

    temp_dir_obj = tempfile.TemporaryDirectory()
    test_dir = Path(temp_dir_obj.name)

    app1 = test_dir / "app1"
    app2 = test_dir / "app2"
    app3_pinned = test_dir / "app3_pinned"
    app1.mkdir()
    app2.mkdir()
    app3_pinned.mkdir()

    # 1. Test Global Install
    print("\n--- TEST 1: Global Installation ---")
    global_target = test_dir / "global_skills" / "telegram-notification"
    code, out, _ = run_cmd(f'python bin/skill-manager.py install --global --target "{global_target}" -y')
    assert code == 0, "Global install failed"
    assert (global_target / "SKILL.md").is_file(), "Global SKILL.md missing"
    assert (global_target / "action.yml").is_file(), "Global action.yml missing"
    print("✅ TEST 1 PASSED: Global installation verified.")

    # 2. Test Project Copy Install
    print("\n--- TEST 2: Project-Level Copy Installation ---")
    code, out, _ = run_cmd(f'python bin/skill-manager.py install --project "{app1}" --agent agentskills -y')
    assert code == 0, "Project install failed"
    installed_skill = app1 / ".agentskills" / "telegram-notification"
    assert (installed_skill / "SKILL.md").is_file(), "Project SKILL.md missing"
    assert (installed_skill / "action.yml").is_file(), "Project action.yml missing"
    assert (installed_skill / ".skill-metadata.json").is_file(), "Metadata file missing"
    print("✅ TEST 2 PASSED: Project copy installation verified.")

    # 3. Test Project Symlink Install
    print("\n--- TEST 3: Project-Level Symlink / Junction Installation ---")
    code, out, _ = run_cmd(f'python bin/skill-manager.py install --project "{app2}" --link -y')
    assert code == 0, "Symlink install failed"
    app2_skill = app2 / ".agentskills" / "telegram-notification"
    assert (app2_skill / "SKILL.md").is_file(), "Symlink SKILL.md missing"
    print("✅ TEST 3 PASSED: Project symlink installation verified.")

    # 4. Test Version Pinning
    print("\n--- TEST 4: Version Pinning ---")
    code, out, _ = run_cmd(f'python bin/skill-manager.py install --project "{app3_pinned}" --pin 1.0.0 -y')
    assert code == 0, "Pinned install failed"
    app3_skill = app3_pinned / ".agentskills" / "telegram-notification"
    meta = app3_skill / ".skill-metadata.json"
    assert meta.is_file(), "Pinned metadata missing"
    assert '"pinnedVersion": "1.0.0"' in meta.read_text(encoding="utf-8")
    print("✅ TEST 4 PASSED: Version pinning verified.")

    # 5. Test Check Updates
    print("\n--- TEST 5: Check Updates ---")
    code, out, _ = run_cmd("python bin/skill-manager.py check-updates")
    assert code == 0, "Check updates failed"
    print("✅ TEST 5 PASSED: Check updates reported correctly.")

    # 6. Test Batch Update
    print("\n--- TEST 6: Batch Update All ---")
    code, out, _ = run_cmd("python bin/skill-manager.py update --all -y")
    assert code == 0, "Batch update failed"
    print("✅ TEST 6 PASSED: Batch update executed cleanly.")

    # 7. Test Rollback Protection on Corruption
    print("\n--- TEST 7: Atomic Rollback on Corrupted Update ---")
    bad_source = test_dir / "bad_source"
    bad_source.mkdir()
    (bad_source / "empty.txt").write_text("broken")

    sys.path.insert(0, str(REPO_ROOT / "bin"))
    import importlib
    sm = importlib.import_module("skill-manager")

    orig_skill_md = (installed_skill / "SKILL.md").read_text(encoding="utf-8")
    success = sm.perform_atomic_update(installed_skill, bad_source, "9.9.9", force=True, skip_confirm=True)
    assert not success, "Atomic update should have failed on corrupted source"
    assert (installed_skill / "SKILL.md").is_file(), "Original SKILL.md must be restored by rollback"
    restored_content = (installed_skill / "SKILL.md").read_text(encoding="utf-8")
    assert restored_content == orig_skill_md, "Content mismatch after rollback"
    print("✅ TEST 7 PASSED: Atomic rollback successfully protected installation from corruption.")

    # 8. Test Uninstall
    print("\n--- TEST 8: Uninstallation ---")
    code, out, _ = run_cmd(f'python bin/skill-manager.py uninstall --project "{app1}" -y')
    assert code == 0, "Uninstall failed"
    assert not (app1 / ".agentskills" / "telegram-notification").exists(), "Directory should be removed"
    print("✅ TEST 8 PASSED: Uninstallation verified.")

    # 9. Test Auto-Detection of Agent Directory
    print("\n--- TEST 9: Agent Directory Auto-Discovery ---")
    app_cursor = test_dir / "app_cursor"
    (app_cursor / ".cursor").mkdir(parents=True)
    code, out, _ = run_cmd(f'python bin/skill-manager.py install --project "{app_cursor}" -y')
    assert code == 0, "Auto-detected install failed"
    assert "Auto-detected agent environment: 'cursor'" in out, "Failed to auto-detect cursor"
    assert (app_cursor / ".cursor" / "skills" / "telegram-notification" / "SKILL.md").is_file(), "Skill missing in .cursor discovery path"
    print("✅ TEST 9 PASSED: Agent discovery directory auto-detection verified.")

    # 10. Test Status Command
    print("\n--- TEST 10: Status Command ---")
    code, out, _ = run_cmd(f'python bin/skill-manager.py status --project "{app_cursor}"')
    assert code == 0, "Status command failed"
    assert "Installed for agent 'cursor'" in out, "Status did not report cursor installation"
    print("✅ TEST 10 PASSED: Status inspection command verified.")

    temp_dir_obj.cleanup()
    print("\n==================================================")
    print("🎉 ALL 10 DISTRIBUTION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    main()
