# Changelog

All notable changes to the `telegram-notification` skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-11-17

### Added
- **Initial Release:** Enterprise-grade continuous integration and continuous deployment Telegram notification skill adhering to the official [Agent Skills specification](https://agentskills.io/specification).
- **Atomic Start-Delete-Replace Lifecycle:**
  - Initial `start` step issues an in-progress card and captures its unique Telegram `message_id` and timestamp.
  - Final `finish` step automatically deletes the obsolete `start` message and posts a single permanent summary card.
  - Guarantees zero notification clutter in team channels and forum topics.
- **Comprehensive Lifecycle Statuses:**
  - Full support for `success`, `failure`, `cancelled`.
  - Advanced operational statuses: `rollback_success` (🔄), `rollback_failed` (🚨), `waiting_approval` (⏳), `warning` (⚠️), and `release` (🏷️).
- **Dual Invocation & Single-Shot Modes:**
  - **Reusable GitHub Composite Action (`action.yml`):** Direct zero-file integration in workflows using `uses: BirtuCan-Software/telegram-notification-skill@v1`.
  - **Standalone POSIX Script (`scripts/telegram-notify.sh`):** Localized curl engine for offline, air-gapped, or specialized runners.
  - **Single-Shot Notifications (`action: notify`):** Send standalone alerts (releases, cron jobs, database backups) without requiring a `start` step.
  - **Inline Fallback Snippet (`assets/snippets/inline-fallback.sh`):** Zero-file copy-paste snippet for inline pipeline embedding.
- **Expandable Details & Error Logging:**
  - Native support for Telegram's `<blockquote expandable>` to display error traces or release notes without cluttering cards.
- **Silent & Low-Priority Alerting:**
  - Optional `silent: true` flag (`disable_notification=true`) for non-disruptive alerts during background jobs or nighttime runs.
- **Card Formatting Standards:**
  - Strict HTML entity escaping (`&`, `<`, `>`) preventing entity parse errors (HTTP 400).
  - Modern card layout with Telegram `<blockquote>`, commit hash, commit message, triggering actor, repository, branch, environment name, and calculated duration (`⏱️ Duration: 1m 45s`).
  - Contextual action buttons and direct links to GitHub Actions runs or failure logs.
  - Optional deployed application URL support (`DEPLOY_URL` / `APP_URL`).
- **Topic Thread Routing:**
  - Native support for Telegram supergroup forum topics via `TELEGRAM_MESSAGE_THREAD_ID`.
- **Cross-Platform Management Utilities:**
  - Core Python engine: `bin/skill-manager.py` (standard library only, zero external dependencies).
  - Native POSIX wrappers: `install.sh`, `update.sh`, `check-updates.sh`, `status.sh`, and `uninstall.sh`.
  - Native CLI wrappers: `bin/skill-manager` (bash) and `bin/skill-manager.ps1` (PowerShell).
  - Automatic agent directory detection for Antigravity, Cursor, Claude Code, Windsurf, and Copilot.
  - Atomic update and backup rollback protection.
- **Automated Test Suite:**
  - Distribution lifecycle test suite (`tests/test_distribution.py`).
  - Unit test suite for notification payload generation and HTML escaping (`tests/test_telegram_notify.py`).
