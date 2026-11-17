# Telegram Bot & Group Setup Guide

This guide provides end-to-end instructions for creating a Telegram bot, configuring permissions, and obtaining the credentials required for automated deployment notifications.

---

## Step 1: Create a Bot with @BotFather

1. Open Telegram and search for the verified account **`@BotFather`**.
2. Start the chat and send `/newbot`.
3. Provide a friendly display name for your bot (e.g. `Acme Deployment Alerts`).
4. Choose a unique username ending in `bot` (e.g. `acme_deploy_alert_bot`).
5. BotFather will return your secret **HTTP API Token**:
   ```
   7123456789:AAFnk9xXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   ```
   This is your `TELEGRAM_BOT_TOKEN`. Keep it strictly confidential.

---

## Step 2: Configure Bot Privacy & Group Rights

In BotFather:
1. Send `/setprivacy` $\rightarrow$ Select your bot $\rightarrow$ Choose **Disable** (or ensure the bot can read messages if using commands).
2. Send `/setjoingroups` $\rightarrow$ Ensure it is set to **Enable**.

---

## Step 3: Add Bot to Your Target Telegram Chat

Depending on your team's workflow:
- **Private Channel:** Add the bot as an Administrator with `Post Messages` permission.
- **Group / Supergroup:** Add the bot as a member, then promote it to **Administrator** with:
  - ✅ **Post Messages**
  - ✅ **Delete Messages** *(Mandatory for Start-Delete-Replace lifecycle)*

---

## Step 4: Retrieve `TELEGRAM_CHAT_ID`

### Method A: Via Telegram Web / Browser
1. In the target group or channel, send a test message: `ping bot`.
2. Open your web browser and navigate to:
   ```
   https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/getUpdates
   ```
3. Locate the `chat` object in the JSON response:
   ```json
   {
     "ok": true,
     "result": [
       {
         "update_id": 987654321,
         "message": {
           "chat": {
             "id": -1001987654321,
             "title": "DevOps Alerts",
             "type": "supergroup"
           }
         }
       }
     ]
   }
   ```
4. Copy the `id` value. For supergroups and channels, it begins with `-100`. This is your `TELEGRAM_CHAT_ID`.

### Method B: Via CLI (curl)
```bash
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates" | grep -o '"chat":{"id":-[0-9]*'
```

---

## Step 5: Retrieve `TELEGRAM_MESSAGE_THREAD_ID` (For Topics)

If your group has Telegram **Topics** enabled and you want notifications posted in a dedicated `#deployments` topic:

1. In Telegram Desktop or Telegram Web, right-click the specific topic name in the left sidebar.
2. Select **Copy Link to Topic**.
3. The link format will be:
   ```
   https://t.me/c/1987654321/42
   ```
4. The final number (`42`) is your `message_thread_id`. Store this as `TELEGRAM_MESSAGE_THREAD_ID`.
*(Note: If you are sending to a standard group or channel without topics, leave this variable unset or empty).*

---

## Step 6: Quick Verification Test

You can test your bot and permissions immediately using curl:

```bash
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_CHAT_ID}" \
  -d "text=🤖 Test notification from Telegram Notification Skill" \
  -d "parse_mode=HTML"
```
If successful, you will receive the message in your Telegram group and the API will return HTTP 200 with `"ok": true`.
