# Troubleshooting Manual: Telegram API

This reference details common issues, error codes, root causes, and verified solutions when sending deployment notifications to Telegram.

---

## 1. HTTP 400: Bad Request: can't parse entities

### Symptom
```json
{"ok":false,"error_code":400,"description":"Bad Request: can't parse entities: can't find end of the entity starting at byte offset..."}
```

### Root Cause
An unescaped `<`, `>`, or `&` appeared inside a commit message, actor name, or branch name while using HTML parse mode.

### Solution
Ensure `html_escape()` is applied to any variable interpolated into HTML tags:
```bash
html_escape() {
  printf '%s' "${1:-}" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
}
```

---

## 2. HTTP 401: Unauthorized

### Symptom
```json
{"ok":false,"error_code":401,"description":"Unauthorized"}
```

### Root Cause
The `TELEGRAM_BOT_TOKEN` is incorrect, truncated, or revoked in BotFather.

### Solution
1. Verify the secret stored in GitHub Secrets matches the exact token provided by `@BotFather`.
2. Check for accidental leading/trailing whitespace.
3. Test manually with:
   ```bash
   curl -s "https://api.telegram.org/bot<TOKEN>/getMe"
   ```
   If valid, it returns `{"ok":true,"result":{"is_bot":true...}}`.

---

## 3. HTTP 400: Bad Request: chat not found

### Symptom
```json
{"ok":false,"error_code":400,"description":"Bad Request: chat not found"}
```

### Root Cause
1. The bot was never added to the group or channel.
2. The `TELEGRAM_CHAT_ID` is missing the `-100` prefix for supergroups/channels.
3. The group was upgraded to a supergroup, which changed its chat ID.

### Solution
1. Re-add the bot to the group.
2. Ensure the ID starts with `-100` (e.g. `-1001987654321`).
3. Re-run `getUpdates` to inspect the latest chat ID.

---

## 4. HTTP 400: Bad Request: message thread not found

### Symptom
```json
{"ok":false,"error_code":400,"description":"Bad Request: message thread not found"}
```

### Root Cause
The `TELEGRAM_MESSAGE_THREAD_ID` points to a topic that was deleted, or the group does not have topics enabled.

### Solution
1. Right-click the topic in Telegram Desktop and copy the link (`https://t.me/c/<CHAT_ID>/<THREAD_ID>`).
2. Update the `TELEGRAM_MESSAGE_THREAD_ID` secret or variable.
3. If sending to the General topic in some forum setups, omit the thread ID or set to `0`.

---

## 5. HTTP 403: Forbidden: bot was kicked / bot is not an admin

### Symptom
```json
{"ok":false,"error_code":403,"description":"Forbidden: bot was kicked from the group"}
```

### Root Cause
The bot was removed or lacks administrator privileges needed to post or delete messages.

### Solution
1. Add the bot back to the group.
2. Promote the bot to Administrator with `Post Messages` and `Delete Messages` permissions enabled.

---

## 6. HTTP 400: Bad Request: message to delete not found

### Symptom
The deletion step fails quietly, or returns:
```json
{"ok":false,"error_code":400,"description":"Bad Request: message to delete not found"}
```

### Root Cause
The `start` message was already deleted (e.g., by a user or another bot), or more than 48 hours have passed.

### Solution
The script handles this gracefully by design using `|| true`. Deletion failure will not fail the pipeline or prevent the final summary message from sending.
