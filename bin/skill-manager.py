#!/usr/bin/env python3
# ==============================================================================
# CLI: skill-manager.py
# Purpose: Universal installation, distribution, versioning, and update manager
#          for Agent Skills adhering to the agentskills.io specification.
# Compatibility: Python 3.8+, cross-platform (Linux, macOS, Windows).
# Zero external pip dependencies (Standard Library only).
# ==============================================================================

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

SKILL_NAME = "telegram-notification"
REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_DIR = Path.home() / ".agentskills"
REGISTRY_FILE = REGISTRY_DIR / "registry.json"
DEFAULT_GLOBAL_DIR = REGISTRY_DIR / "skills" / SKILL_NAME

DISCOVERY_PATHS = {
    "agentskills": Path(".agentskills") / SKILL_NAME,
    "antigravity": Path(".gemini") / "skills" / SKILL_NAME,
    "cursor": Path(".cursor") / "skills" / SKILL_NAME,
    "claude": Path(".claude") / "skills" / SKILL_NAME,
    "windsurf": Path(".windsurf") / "skills" / SKILL_NAME,
    "copilot": Path(".github") / "skills" / SKILL_NAME,
}

def detect_agent_environment(project_dir: Path) -> Tuple[str, Path]:
    """Auto-detect target agent discovery path by inspecting project directories."""
    detection_order = [
        ("cursor", Path(".cursor")),
        ("claude", Path(".claude")),
        ("antigravity", Path(".gemini")),
        ("windsurf", Path(".windsurf")),
        ("agentskills", Path(".agentskills")),
        ("copilot", Path(".github")),
    ]
    for agent_key, check_dir in detection_order:
        if (project_dir / check_dir).is_dir():
            return agent_key, DISCOVERY_PATHS[agent_key]
    return "agentskills", DISCOVERY_PATHS["agentskills"]

# ------------------------------------------------------------------------------
# Version & Semantic Helpers
# ------------------------------------------------------------------------------

def parse_semver(version_str: str) -> Tuple[int, int, int]:
    """Extract (major, minor, patch) tuple from version string."""
    clean = re.sub(r"^[vV]", "", version_str.strip())
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", clean)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return (0, 0, 0)

def compare_versions(v1: str, v2: str) -> int:
    """Returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal."""
    p1 = parse_semver(v1)
    p2 = parse_semver(v2)
    if p1 > p2:
        return 1
    elif p1 < p2:
        return -1
    return 0

def get_repo_version(repo_dir: Path) -> str:
    """Retrieve version from skill.json or SKILL.md frontmatter."""
    manifest_path = repo_dir / "skill.json"
    if manifest_path.is_file():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "version" in data:
                    return str(data["version"])
        except Exception:
            pass

    skill_md = repo_dir / "SKILL.md"
    if skill_md.is_file():
        try:
            content = skill_md.read_text(encoding="utf-8")
            match = re.search(r"version:\s*([0-9\.]+)", content)
            if match:
                return match.group(1)
        except Exception:
            pass

    return "1.0.0"

# ------------------------------------------------------------------------------
# Registry Management
# ------------------------------------------------------------------------------

def load_registry() -> Dict[str, Any]:
    """Load ~/.agentskills/registry.json or return default empty structure."""
    if not REGISTRY_FILE.is_file():
        return {"version": "1.0", "global": None, "projects": []}
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Warning: Could not read registry file: {e}")
        return {"version": "1.0", "global": None, "projects": []}

def save_registry(registry: Dict[str, Any]) -> None:
    """Save registry to ~/.agentskills/registry.json."""
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

def register_installation(target_path: Path, is_global: bool, mode: str, version: str,
                          pinned_version: Optional[str] = None, agent: str = "agentskills",
                          project_root: Optional[Path] = None) -> None:
    """Update registry with new or updated installation record."""
    reg = load_registry()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if is_global:
        reg["global"] = {
            "path": str(target_path.resolve()),
            "mode": mode,
            "version": version,
            "installedAt": now_iso,
        }
    else:
        proj_str = str((project_root or target_path.parent.parent).resolve())
        skill_str = str(target_path.resolve())

        # Update existing or append new
        updated = False
        for p in reg.get("projects", []):
            if p.get("skillPath") == skill_str or p.get("projectPath") == proj_str:
                p["skillPath"] = skill_str
                p["projectPath"] = proj_str
                p["agent"] = agent
                p["mode"] = mode
                p["installedVersion"] = version
                p["pinnedVersion"] = pinned_version
                p["lastUpdated"] = now_iso
                updated = True
                break
        if not updated:
            reg.setdefault("projects", []).append({
                "projectPath": proj_str,
                "skillPath": skill_str,
                "agent": agent,
                "mode": mode,
                "installedVersion": version,
                "pinnedVersion": pinned_version,
                "installedAt": now_iso,
                "lastUpdated": now_iso,
            })

    save_registry(reg)

def unregister_installation(target_path: Path, is_global: bool) -> None:
    """Remove an installation from the central registry."""
    reg = load_registry()
    target_str = str(target_path.resolve())

    if is_global:
        reg["global"] = None
    else:
        reg["projects"] = [
            p for p in reg.get("projects", [])
            if p.get("skillPath") != target_str and p.get("projectPath") != target_str
        ]

    save_registry(reg)

def prune_stale_installations() -> int:
    """Automatically remove registry records whose paths no longer exist on disk."""
    reg = load_registry()
    changed = False

    if reg.get("global"):
        gp = Path(reg["global"].get("path", ""))
        if not gp.exists():
            reg["global"] = None
            changed = True

    valid_projects = []
    for p in reg.get("projects", []):
        sp = Path(p.get("skillPath", ""))
        pp = Path(p.get("projectPath", ""))
        if sp.exists() and pp.exists():
            valid_projects.append(p)
        else:
            changed = True

    if changed:
        reg["projects"] = valid_projects
        save_registry(reg)
    return len(valid_projects)

# ------------------------------------------------------------------------------
# Linking & File Copy Helpers
# ------------------------------------------------------------------------------

def create_directory_link(source_dir: Path, target_dir: Path) -> bool:
    """Create a symbolic link or Windows directory junction."""
    source_dir = source_dir.resolve()
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    if target_dir.exists() or target_dir.is_symlink():
        if target_dir.is_symlink() or (sys.platform == "win32" and not target_dir.is_file()):
            try:
                if sys.platform == "win32":
                    subprocess.run(f'rmdir "{target_dir}"', shell=True, check=True, stdout=subprocess.DEVNULL)
                else:
                    target_dir.unlink()
            except Exception:
                shutil.rmtree(target_dir, ignore_errors=True)
        else:
            shutil.rmtree(target_dir, ignore_errors=True)

    # Attempt standard symlink first
    try:
        os.symlink(str(source_dir), str(target_dir), target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        pass

    # Windows Directory Junction fallback (requires no admin privileges)
    if sys.platform == "win32":
        try:
            cmd = f'mklink /J "{target_dir}" "{source_dir}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return True
        except Exception:
            pass

    return False

def copy_skill_tree(source_dir: Path, target_dir: Path) -> None:
    """Copy skill directory excluding .git, caches, and backups."""
    source_resolved = source_dir.resolve()
    target_resolved = target_dir.resolve()
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    def ignore_patterns(folder, names):
        folder_resolved = Path(folder).resolve()
        ignored = {".git", ".bak", "__pycache__", ".DS_Store", ".test_sandbox", ".venv", "node_modules"}
        to_ignore = set()
        for n in names:
            item_path = (folder_resolved / n).resolve()
            if item_path == target_resolved or item_path in target_resolved.parents:
                to_ignore.add(n)
            elif n in ignored or n.endswith(".tmp") or n.startswith(".bak_"):
                to_ignore.add(n)
        return to_ignore

    if target_dir.exists():
        shutil.rmtree(target_dir)

    shutil.copytree(source_dir, target_dir, ignore=ignore_patterns, symlinks=True)

def verify_skill_integrity(skill_dir: Path) -> Tuple[bool, str]:
    """Verify that a directory contains a valid Agent Skills specification layout."""
    if not skill_dir.is_dir():
        return False, f"Directory does not exist: {skill_dir}"

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return False, f"Missing required SKILL.md in {skill_dir}"

    try:
        content = skill_md.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return False, "SKILL.md is missing initial YAML frontmatter delimiter (---)"
        if not re.search(r"name:\s*[a-z0-9\-]+", content):
            return False, "SKILL.md frontmatter is missing valid 'name' attribute"
    except Exception as e:
        return False, f"Failed reading SKILL.md: {e}"

    return True, "Valid Agent Skill"

# ------------------------------------------------------------------------------
# Core Actions: Install, Update, Check, Uninstall
# ------------------------------------------------------------------------------

def cmd_install(args: argparse.Namespace) -> int:
    source_dir = REPO_ROOT
    current_ver = get_repo_version(source_dir)

    is_global = args.global_install
    use_link = args.link
    pinned_version = args.pin

    if is_global:
        target_dir = Path(args.target).resolve() if args.target else DEFAULT_GLOBAL_DIR
        project_root = None
        agent_name = "global"
        print(f"📦 Installing {SKILL_NAME} globally...")
    else:
        project_root = Path(args.project).resolve() if args.project else Path.cwd()
        if not project_root.is_dir():
            print(f"❌ Error: Project path does not exist: {project_root}")
            return 1

        if args.agent:
            agent_name = args.agent
            subpath = DISCOVERY_PATHS.get(agent_name, DISCOVERY_PATHS["agentskills"])
        else:
            agent_name, subpath = detect_agent_environment(project_root)
            if agent_name != "agentskills":
                print(f"🔍 Auto-detected agent environment: '{agent_name}'")

        target_dir = (project_root / subpath).resolve()
        print(f"📦 Installing {SKILL_NAME} to project: {project_root}")
        print(f"   Target discovery directory: {target_dir}")

    # Check if target already exists
    if target_dir.exists() and not args.force:
        print(f"⚠️ Target destination already exists: {target_dir}")
        if not args.yes:
            ans = input("Do you wish to overwrite this installation? [y/N]: ").strip().lower()
            if ans != "y":
                print("Installation aborted.")
                return 0

    mode = "symlink" if use_link else "copy"

    if use_link:
        print(f"🔗 Establishing symbolic link from {source_dir} -> {target_dir}...")
        success = create_directory_link(source_dir, target_dir)
        if not success:
            print("⚠️ Warning: Symbolic link could not be created. Falling back to self-contained copy.")
            copy_skill_tree(source_dir, target_dir)
            mode = "copy"
    else:
        print(f"📋 Copying skill tree to {target_dir}...")
        copy_skill_tree(source_dir, target_dir)

    # Verify integrity
    valid, err = verify_skill_integrity(target_dir)
    if not valid:
        print(f"❌ Verification failed: {err}")
        return 1

    # Write per-installation metadata file
    meta_file = target_dir / ".skill-metadata.json"
    try:
        meta_data = {
            "name": SKILL_NAME,
            "installedVersion": current_ver,
            "pinnedVersion": pinned_version,
            "installationMode": mode,
            "sourcePath": str(source_dir),
            "installedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Could not write .skill-metadata.json: {e}")

    # Register in central registry
    register_installation(
        target_path=target_dir,
        is_global=is_global,
        mode=mode,
        version=current_ver,
        pinned_version=pinned_version,
        agent=agent_name,
        project_root=project_root,
    )

    print(f"✅ Successfully installed {SKILL_NAME} v{current_ver} ({mode})!")
    if pinned_version:
        print(f"📌 Version pinned to: {pinned_version}")
    return 0

def cmd_status(args: argparse.Namespace) -> int:
    prune_stale_installations()
    source_ver = get_repo_version(REPO_ROOT)
    reg = load_registry()

    print("==================================================")
    print(f"ℹ️  Skill Status: {SKILL_NAME} (Latest: v{source_ver})")
    print(f"   Repository Source: {REPO_ROOT}")
    print("==================================================")

    # 1. Global installation
    print("\n🌐 Global Installation:")
    if reg.get("global") and Path(reg["global"]["path"]).exists():
        g = reg["global"]
        print(f"   Status:  ✅ Installed (v{g.get('version')}, {g.get('mode')})")
        print(f"   Path:    {g.get('path')}")
        print(f"   Updated: {g.get('installedAt', 'unknown')}")
    else:
        print("   Status:  ⭕ Not installed globally.")

    # 2. Checked Project Directory
    proj_dir = Path(args.project).resolve() if getattr(args, "project", None) else Path.cwd()
    print(f"\n📂 Checked Project Directory: {proj_dir}")
    found_local = False
    for agent_key, subpath in DISCOVERY_PATHS.items():
        candidate = proj_dir / subpath
        if candidate.exists():
            found_local = True
            mode = "symlink" if (candidate.is_symlink() or (sys.platform == "win32" and os.path.islink(str(candidate)))) else "copy"
            ver = get_repo_version(candidate)
            meta_file = candidate / ".skill-metadata.json"
            pin = None
            if meta_file.is_file():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        pin = json.load(f).get("pinnedVersion")
                except Exception:
                    pass
            print(f"   Status:  ✅ Installed for agent '{agent_key}' (v{ver}, {mode})")
            print(f"   Path:    {candidate}")
            if pin:
                print(f"   Pinned:  🔒 v{pin}")
            break
    if not found_local:
        print("   Status:  ⭕ No skill installation detected in this directory.")

    # 3. All Registered Projects
    projects = reg.get("projects", [])
    if projects:
        print(f"\n📑 Registered Managed Projects ({len(projects)} total):")
        for p in projects:
            sp = Path(p.get("skillPath", ""))
            status_icon = "✅" if sp.exists() else "❌ (missing)"
            pin_info = f" [Pinned: v{p.get('pinnedVersion')}]" if p.get("pinnedVersion") else ""
            print(f"   • {status_icon} {p.get('projectPath')} ({p.get('agent', 'agentskills')}) -> v{p.get('installedVersion')} ({p.get('mode')}){pin_info}")

    print("\n" + "=" * 50)
    return 0

def cmd_check_updates(args: argparse.Namespace) -> int:
    prune_stale_installations()
    source_ver = get_repo_version(REPO_ROOT)
    reg = load_registry()

    print(f"🔍 Checking updates for {SKILL_NAME} (Latest available: v{source_ver})...\n")

    items = []
    if reg.get("global"):
        g = reg["global"]
        items.append(("Global", g.get("path"), g.get("mode"), g.get("version"), None))

    for p in reg.get("projects", []):
        items.append((
            f"Project ({p.get('agent', 'agentskills')})",
            p.get("skillPath"),
            p.get("mode"),
            p.get("installedVersion"),
            p.get("pinnedVersion"),
        ))

    # Also check current working directory if not registered
    cwd_skill = Path.cwd() / ".agentskills" / SKILL_NAME
    if cwd_skill.is_dir() and not any(str(cwd_skill.resolve()) == str(item[1]) for item in items):
        installed_v = get_repo_version(cwd_skill)
        items.append(("Local (CWD)", str(cwd_skill.resolve()), "copy", installed_v, None))

    if not items:
        print("No managed installations found in registry or current working directory.")
        print(f"Run '{sys.argv[0]} install --global' or '{sys.argv[0]} install --project' to install.")
        return 0

    print(f"{'Target':<22} {'Version':<10} {'Mode':<10} {'Status':<18} {'Path'}")
    print("-" * 80)

    updates_found = 0
    for target_label, path_str, mode, inst_ver, pin in items:
        path = Path(path_str) if path_str else None
        if not path or not path.exists():
            status = "❌ Missing path"
        elif mode == "symlink":
            status = "🟢 Live linked"
        elif pin:
            status = f"📌 Pinned ({pin})"
        elif compare_versions(source_ver, inst_ver or "0.0.0") > 0:
            status = f"🟡 Update: v{source_ver}"
            updates_found += 1
        else:
            status = "✅ Up-to-date"

        ver_display = f"v{inst_ver}" if inst_ver else "unknown"
        print(f"{target_label:<22} {ver_display:<10} {str(mode):<10} {status:<18} {path_str}")

    print("-" * 80)
    if updates_found > 0:
        print(f"\n💡 {updates_found} installation(s) can be upgraded.")
        print(f"   Run '{sys.argv[0]} update' or '{sys.argv[0]} update --all' to apply.")
    else:
        print("\nAll installations are up-to-date or pinned.")
    return 0

def show_update_preview(installed_ver: str, target_ver: str) -> None:
    """Print changelog preview between installed and target version."""
    changelog_file = REPO_ROOT / "CHANGELOG.md"
    print(f"\n📄 Update Preview: v{installed_ver} -> v{target_ver}")
    print("=" * 60)
    if changelog_file.is_file():
        try:
            content = changelog_file.read_text(encoding="utf-8")
            match = re.search(r"##\s*\[" + re.escape(target_ver) + r"\][^\n]*\n(.*?)(?=\n##\s*\[|\Z)", content, re.DOTALL)
            if match:
                print(match.group(1).strip())
            else:
                lines = content.splitlines()[:25]
                print("\n".join(lines))
        except Exception:
            print("Changelog summary unavailable.")
    else:
        print("No CHANGELOG.md found in source repository.")
    print("=" * 60 + "\n")

def perform_atomic_update(target_path: Path, source_dir: Path, target_version: str,
                          force: bool = False, skip_confirm: bool = False) -> bool:
    """Safely update an existing skill installation with backup and rollback."""
    if not target_path.exists():
        print(f"❌ Error: Installation path not found: {target_path}")
        return False

    meta_file = target_path / ".skill-metadata.json"
    pinned_version = None
    installed_ver = get_repo_version(target_path)

    if meta_file.is_file():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                m = json.load(f)
                pinned_version = m.get("pinnedVersion")
                installed_ver = m.get("installedVersion", installed_ver)
        except Exception:
            pass

    if target_path.is_symlink() or (sys.platform == "win32" and not target_path.is_file() and not os.listdir(target_path)):
        print(f"ℹ️ {target_path} is a symbolic link. Changes to central repository reflect automatically.")
        return True

    if pinned_version and not force:
        print(f"🔒 Skipped: Installation at {target_path} is pinned to v{pinned_version}.")
        print("   Use --force to override the version pin.")
        return False

    if compare_versions(installed_ver, target_version) == 0 and not force:
        print(f"✅ {target_path} is already at latest version (v{installed_ver}).")
        return True

    show_update_preview(installed_ver, target_version)

    if not skip_confirm:
        ans = input(f"Apply update to {target_path}? [y/N]: ").strip().lower()
        if ans != "y":
            print("Update cancelled by user.")
            return False

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = target_path.parent / f"{target_path.name}.bak_{timestamp}"

    print(f"💾 Creating safety backup at: {backup_path.name}...")
    try:
        shutil.copytree(target_path, backup_path, symlinks=True)
    except Exception as e:
        print(f"❌ Could not create pre-update backup: {e}. Aborting update.")
        return False

    print(f"🚀 Updating files from v{installed_ver} to v{target_version}...")
    try:
        copy_skill_tree(source_dir, target_path)

        valid, err = verify_skill_integrity(target_path)
        if not valid:
            raise RuntimeError(f"Integrity check failed: {err}")

        new_meta = {
            "name": SKILL_NAME,
            "installedVersion": target_version,
            "pinnedVersion": pinned_version if force else None,
            "installationMode": "copy",
            "sourcePath": str(source_dir),
            "lastUpdated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        with open(target_path / ".skill-metadata.json", "w", encoding="utf-8") as f:
            json.dump(new_meta, f, indent=2)

        shutil.rmtree(backup_path, ignore_errors=True)
        print(f"✅ Successfully updated {target_path} to v{target_version}!")
        return True

    except Exception as e:
        print(f"❌ Update failed with error: {e}")
        print("🔄 Rolling back to previous state from backup...")
        shutil.rmtree(target_path, ignore_errors=True)
        shutil.move(backup_path, target_path)
        print("🛡️ Rollback complete. Original installation restored.")
        return False

def cmd_update(args: argparse.Namespace) -> int:
    source_ver = get_repo_version(REPO_ROOT)
    reg = load_registry()

    if args.all:
        print(f"🔄 Updating all managed installations to v{source_ver}...")
        targets = []
        if reg.get("global") and reg["global"].get("mode") == "copy":
            targets.append(Path(reg["global"]["path"]))

        for p in reg.get("projects", []):
            if p.get("mode") == "copy" and p.get("skillPath"):
                targets.append(Path(p["skillPath"]))

        if not targets:
            print("No copy-based installations to update.")
            return 0

        success_count = 0
        for t in targets:
            print(f"\n--- Updating {t} ---")
            if perform_atomic_update(t, REPO_ROOT, source_ver, force=args.force, skip_confirm=args.yes):
                success_count += 1
                register_installation(t, is_global=False, mode="copy", version=source_ver)

        print(f"\n🎉 Finished batch update: {success_count}/{len(targets)} installations updated successfully.")
        return 0

    if args.global_target:
        if not reg.get("global"):
            print("Global installation not found in registry.")
            return 1
        target_path = Path(reg["global"]["path"])
    elif args.project:
        target_path = (Path(args.project) / DISCOVERY_PATHS["agentskills"]).resolve()
    else:
        target_path = (Path.cwd() / DISCOVERY_PATHS["agentskills"]).resolve()
        if not target_path.exists():
            for sp in DISCOVERY_PATHS.values():
                candidate = (Path.cwd() / sp).resolve()
                if candidate.exists():
                    target_path = candidate
                    break

    if not target_path.exists():
        print(f"❌ Error: No installation found at {target_path}.")
        print("Specify the installation path or use --global or --all.")
        return 1

    success = perform_atomic_update(target_path, REPO_ROOT, source_ver, force=args.force, skip_confirm=args.yes)
    if success:
        register_installation(target_path, is_global=args.global_target, mode="copy", version=source_ver)
        return 0
    return 1

def cmd_uninstall(args: argparse.Namespace) -> int:
    reg = load_registry()

    if args.all:
        print(f"⚠️ Warning: This will uninstall all managed installations of {SKILL_NAME}.")
        if not args.yes:
            ans = input("Are you sure you want to proceed? [y/N]: ").strip().lower()
            if ans != "y":
                print("Aborted.")
                return 0

        if reg.get("global") and Path(reg["global"]["path"]).exists():
            shutil.rmtree(reg["global"]["path"], ignore_errors=True)
            print(f"🗑️ Removed global installation: {reg['global']['path']}")

        for p in reg.get("projects", []):
            sp = Path(p.get("skillPath", ""))
            if sp.exists():
                shutil.rmtree(sp, ignore_errors=True)
                print(f"🗑️ Removed project installation: {sp}")

        save_registry({"version": "1.0", "global": None, "projects": []})
        print("✅ All installations uninstalled successfully.")
        return 0

    if args.global_target:
        if not reg.get("global") or not Path(reg["global"]["path"]).exists():
            print("No global installation found.")
            return 1
        target_path = Path(reg["global"]["path"])
        is_global = True
    else:
        proj_dir = Path(args.project).resolve() if args.project else Path.cwd()
        target_path = proj_dir / DISCOVERY_PATHS["agentskills"]
        is_global = False
        if not target_path.exists():
            for sp in DISCOVERY_PATHS.values():
                candidate = proj_dir / sp
                if candidate.exists():
                    target_path = candidate
                    break

    if not target_path.exists():
        print(f"❌ No installation found at {target_path}")
        return 1

    if not args.yes:
        ans = input(f"Remove installation at {target_path}? [y/N]: ").strip().lower()
        if ans != "y":
            print("Uninstall cancelled.")
            return 0

    is_junction_or_link = target_path.is_symlink() or (sys.platform == "win32" and os.path.islink(str(target_path)))
    if is_junction_or_link:
        try:
            if sys.platform == "win32":
                subprocess.run(f'rmdir "{target_path}"', shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                target_path.unlink()
        except Exception:
            shutil.rmtree(target_path, ignore_errors=True)
    else:
        shutil.rmtree(target_path, ignore_errors=True)

    unregister_installation(target_path, is_global)
    print(f"✅ Uninstalled {SKILL_NAME} from {target_path}.")
    return 0

# ------------------------------------------------------------------------------
# Entrypoint & CLI Parser
# ------------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="skill-manager",
        description="Universal Agent Skills Installation, Distribution & Update Manager",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Management commands")

    p_inst = subparsers.add_parser("install", help="Install the skill globally or into a project")
    p_inst.add_argument("-g", "--global", dest="global_install", action="store_true", help="Install into central user directory")
    p_inst.add_argument("-p", "--project", type=str, help="Target project root directory (default: current directory)")
    p_inst.add_argument("-t", "--target", type=str, help="Custom destination folder")
    p_inst.add_argument("-l", "--link", action="store_true", help="Create a live symbolic link instead of copying")
    p_inst.add_argument("--pin", type=str, help="Pin installation to a specific version")
    p_inst.add_argument("--agent", choices=list(DISCOVERY_PATHS.keys()), default=None, help="Target agent discovery layout (auto-detected if omitted)")
    p_inst.add_argument("-f", "--force", action="store_true", help="Overwrite existing installation without prompt")
    p_inst.add_argument("-y", "--yes", action="store_true", help="Skip interactive confirmation")

    p_chk = subparsers.add_parser("check-updates", help="Check for available updates across managed installations")
    p_chk.add_argument("-s", "--status", action="store_true", help="Display full installation and environment status")

    p_stat = subparsers.add_parser("status", help="Display complete status of all global and project skill installations")
    p_stat.add_argument("-p", "--project", type=str, help="Specific project directory to inspect (default: current directory)")

    p_upd = subparsers.add_parser("update", help="Update installed skill(s)")
    p_upd.add_argument("-a", "--all", action="store_true", help="Update all registered installations")
    p_upd.add_argument("-g", "--global", dest="global_target", action="store_true", help="Update global installation")
    p_upd.add_argument("-p", "--project", type=str, help="Project directory to update")
    p_upd.add_argument("-f", "--force", action="store_true", help="Force update even if installation is pinned")
    p_upd.add_argument("-y", "--yes", action="store_true", help="Skip interactive confirmation")

    p_un = subparsers.add_parser("uninstall", help="Uninstall skill")
    p_un.add_argument("-g", "--global", dest="global_target", action="store_true", help="Uninstall global installation")
    p_un.add_argument("-p", "--project", type=str, help="Project directory to uninstall")
    p_un.add_argument("-a", "--all", action="store_true", help="Uninstall all managed installations")
    p_un.add_argument("-y", "--yes", action="store_true", help="Skip interactive confirmation")

    args = parser.parse_args()

    if args.subcommand == "install":
        return cmd_install(args)
    elif args.subcommand == "check-updates":
        if getattr(args, "status", False):
            return cmd_status(args)
        return cmd_check_updates(args)
    elif args.subcommand == "status":
        return cmd_status(args)
    elif args.subcommand == "update":
        return cmd_update(args)
    elif args.subcommand == "uninstall":
        return cmd_uninstall(args)
    else:
        parser.print_help()
        return 0

if __name__ == "__main__":
    sys.exit(main())
