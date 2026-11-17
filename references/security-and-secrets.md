# Security & Secrets Best Practices

This reference covers the security architecture for managing Telegram API credentials and safeguarding CI/CD pipelines.

---

## 1. Credential Classification

| Variable | Sensitivity Level | Recommended Storage Location |
| :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | **Critical Secret** | GitHub Repository or Environment Secrets |
| `TELEGRAM_CHAT_ID` | **Sensitive Identifier** | GitHub Secrets (or Repo Variables for public channels) |
| `TELEGRAM_MESSAGE_THREAD_ID` | Low / Public | GitHub Variables or Secrets |
| `DEPLOY_URL` | Non-sensitive | GitHub Repository or Environment Variables |

---

## 2. Preventing Credential Exposure in Logs

1. **Automatic GitHub Actions Masking:**
   Any value defined in `secrets.*` is automatically masked with `***` by the GitHub Actions runner in build logs.
2. **Never Echo Unmasked Secrets:**
   Never output `echo $TELEGRAM_BOT_TOKEN` in shell steps.
3. **HTTP Header & URL Masking:**
   Telegram API tokens are passed in the request URL (`https://api.telegram.org/bot<TOKEN>/sendMessage`). The helper script uses curl with `-s -S` to suppress verbose URL printing in standard output.

---

## 3. Bot Permission Hardening

Apply the principle of least privilege when adding the bot to your Telegram group:
- **Required:**
  - `Post Messages`
  - `Delete Messages` (for Start-Delete-Replace)
- **Do NOT grant:**
  - `Add Administrators`
  - `Change Group Info`
  - `Ban Users`
  - `Pin Messages` (unless required for custom workflows)

---

## 4. Fork Safety & Environment Protection

In open-source or multi-contributor repositories:
- Workflows triggered from pull requests by external forks do not have access to repository secrets by default.
- The `if: env.TELEGRAM_BOT_TOKEN != ''` conditional guard prevents failed notification attempts on forks.
