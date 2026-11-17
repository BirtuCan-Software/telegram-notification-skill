import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (REPO_ROOT / "scripts" / "telegram-notify.sh").as_posix()

def get_bash_executable():
    """Find a functional bash executable across Windows, macOS, and Linux."""
    if sys.platform == "win32":
        git_bash = Path("C:/Program Files/Git/bin/bash.exe")
        if git_bash.is_file():
            return str(git_bash)
        git_usr_bash = Path("C:/Program Files/Git/usr/bin/bash.exe")
        if git_usr_bash.is_file():
            return str(git_usr_bash)

    candidate = shutil.which("bash")
    if candidate:
        return candidate
    return "bash"

class TestTelegramNotificationScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bash_bin = get_bash_executable()

    def setUp(self):
        self.base_env = os.environ.copy()
        for var in [
            "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_MESSAGE_THREAD_ID",
            "DEPLOY_URL", "APP_URL", "CPANEL_FRONTEND_DOMAIN", "NOTIFICATION_TITLE",
            "NOTIFICATION_DETAILS", "DETAILS", "NOTIFICATION_SILENT", "SILENT",
            "GITHUB_REPOSITORY", "GITHUB_REF_NAME", "GITHUB_ENVIRONMENT",
            "GITHUB_TRIGGERING_ACTOR", "GITHUB_ACTOR", "GITHUB_SERVER_URL",
            "GITHUB_RUN_ID", "GITHUB_RUN_NUMBER", "GITHUB_SHA", "COMMIT_MESSAGE"
        ]:
            self.base_env.pop(var, None)

    def run_bash_script(self, args, env):
        bash_cmd = [self.bash_bin, SCRIPT_PATH] + args
        res = subprocess.run(bash_cmd, env=env, capture_output=True, text=True)
        return res

    def test_guard_missing_credentials(self):
        """Script should gracefully exit 0 and log warning if secrets are missing."""
        res = self.run_bash_script(["start"], self.base_env)
        self.assertEqual(res.returncode, 0)
        self.assertIn("not configured. Skipping notification", res.stdout)

    def test_html_escaping_logic(self):
        """Test HTML escaping within bash subshell."""
        test_snippet = 'html_escape() { printf \'%s\' "${1:-}" | sed -e \'s/&/\\&amp;/g\' -e \'s/</\\&lt;/g\' -e \'s/>/\\&gt;/g\'; }; html_escape "feat(auth): fix <token> & update [v1.0]"'
        cmd = [self.bash_bin, "-c", test_snippet]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.stdout.strip(), "feat(auth): fix &lt;token&gt; &amp; update [v1.0]")

    def test_script_syntax_and_usage(self):
        """Test running without arguments prints usage and exits 1."""
        env = self.base_env.copy()
        env["TELEGRAM_BOT_TOKEN"] = "123456:fake-token"
        env["TELEGRAM_CHAT_ID"] = "-100123456789"
        res = self.run_bash_script([], env)
        self.assertEqual(res.returncode, 1)
        self.assertIn("Usage:", res.stdout)
        self.assertIn("notify", res.stdout)

    def test_status_resolution_meta(self):
        """Verify status mapping for success, failure, rollback, approval, warning, and release."""
        test_cases = [
            ("success", "✅", "Deployment Successful"),
            ("failure", "❌", "Deployment Failed"),
            ("cancelled", "⚠️", "Deployment Cancelled"),
            ("rollback_success", "🔄", "Deployment Rollback Successful"),
            ("rollback_failed", "🚨", "Deployment Rollback Failed"),
            ("waiting_approval", "⏳", "Deployment Awaiting Approval"),
            ("warning", "⚠️", "Deployment Completed with Warnings"),
            ("release", "🏷️", "Release Published"),
        ]
        for status, exp_icon, exp_header in test_cases:
            snippet = f'''
            source "{SCRIPT_PATH}" __source__
            resolve_status_meta "{status}"
            echo "$ICON|$HEADER"
            '''
            cmd = [self.bash_bin, "-c", snippet]
            res = subprocess.run(cmd, capture_output=True, text=True)
            output = res.stdout.strip()
            self.assertIn(exp_icon, output, f"Icon mismatch for {status}")
            self.assertIn(exp_header, output, f"Header mismatch for {status}")

    def test_expandable_details_formatting(self):
        """Verify build_details_block generates properly escaped expandable blockquote."""
        snippet = f'''
        source "{SCRIPT_PATH}" __source__
        build_details_block "Error: <div> & failed [auth]"
        '''
        cmd = [self.bash_bin, "-c", snippet]
        res = subprocess.run(cmd, capture_output=True, text=True)
        output = res.stdout.strip()
        self.assertIn("<blockquote expandable>", output)
        self.assertIn("Error: &lt;div&gt; &amp; failed [auth]", output)
        self.assertIn("</blockquote>", output)

    def test_action_yml_structure(self):
        """Verify action.yml contains valid metadata, required inputs and outputs."""
        action_file = REPO_ROOT / "action.yml"
        self.assertTrue(action_file.is_file(), "action.yml missing")
        content = action_file.read_text(encoding="utf-8")
        self.assertIn("name:", content)
        self.assertIn("inputs:", content)
        self.assertIn("bot_token:", content)
        self.assertIn("chat_id:", content)
        self.assertIn("message_thread_id:", content)
        self.assertIn("action:", content)
        self.assertIn("status:", content)
        self.assertIn("details:", content)
        self.assertIn("silent:", content)
        self.assertIn("outputs:", content)
        self.assertIn("message_id:", content)
        self.assertIn("runs:", content)
        self.assertIn("using: \"composite\"", content)

    def test_skill_json_structure(self):
        """Verify skill.json metadata matches specification."""
        import json
        skill_file = REPO_ROOT / "skill.json"
        self.assertTrue(skill_file.is_file(), "skill.json missing")
        with open(skill_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data.get("name"), "telegram-notification")
        self.assertEqual(data.get("version"), "1.0.0")
        self.assertEqual(data.get("entrypoint"), "SKILL.md")
        self.assertIn("antigravity", data.get("discoveryPaths", {}))
        self.assertIn("cursor", data.get("discoveryPaths", {}))
        self.assertIn("claude", data.get("discoveryPaths", {}))

if __name__ == "__main__":
    unittest.main()
