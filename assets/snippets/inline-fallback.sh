#!/usr/bin/env bash
# ==============================================================================
# Snippet: Inline Telegram Notification Fallback
# Can be copied directly into GitHub Actions step 'run:' block without any files.
# ==============================================================================

# Required environment variables:
# TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
# Optional: TELEGRAM_MESSAGE_THREAD_ID, DEPLOY_URL, START_MSG_ID, START_TIME, JOB_STATUS

API_URL="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}"
BRANCH="${GITHUB_REF_NAME:-main}"
ENV_NAME="${GITHUB_ENVIRONMENT:-$BRANCH}"
ACTOR="${GITHUB_TRIGGERING_ACTOR:-${GITHUB_ACTOR:-developer}}"
COMMIT_HASH="${GITHUB_SHA:0:7}"
RAW_MSG="${COMMIT_MESSAGE:-$(git log -1 --pretty=format:'%s' 2>/dev/null || echo 'Manual Trigger')}"
COMMIT_MSG=$(printf '%s' "$RAW_MSG" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')
RUN_URL="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"

EXTRA_ARGS=()
[ -n "${TELEGRAM_MESSAGE_THREAD_ID:-}" ] && [ "$TELEGRAM_MESSAGE_THREAD_ID" != "0" ] && EXTRA_ARGS+=(--data-urlencode "message_thread_id=${TELEGRAM_MESSAGE_THREAD_ID}")

# 1. If finishing: delete previous start message if provided
if [ -n "${START_MSG_ID:-}" ]; then
  curl -s -S -X POST "${API_URL}/deleteMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "message_id=${START_MSG_ID}" >/dev/null 2>&1 || true
fi

# 2. Build duration line if finishing
DURATION_LINE=""
if [ -n "${START_TIME:-}" ]; then
  ELAPSED=$(( $(date +%s) - START_TIME ))
  MINS=$(( ELAPSED / 60 ))
  SECS=$(( ELAPSED % 60 ))
  DURATION_LINE="⏱️ <b>Duration:</b> ${MINS}m ${SECS}s"$'\n'
fi

# 3. Choose icon and title based on status
STATUS="${JOB_STATUS:-success}"
case "$STATUS" in
  started) ICON="🚀"; TITLE="Deployment Started"; LINK_TEXT="View Actions Run #${GITHUB_RUN_NUMBER} →" ;;
  success) ICON="✅"; TITLE="Deployment Successful"; LINK_TEXT="View Actions Run #${GITHUB_RUN_NUMBER} →" ;;
  cancelled) ICON="⚠️"; TITLE="Deployment Cancelled"; LINK_TEXT="View Actions Run #${GITHUB_RUN_NUMBER} →" ;;
  *) ICON="❌"; TITLE="Deployment Failed"; LINK_TEXT="View Failure Logs #${GITHUB_RUN_NUMBER} →" ;;
esac

TEXT="${ICON} <b>${TITLE}</b>"$'\n\n'
TEXT+="<blockquote>"
TEXT+="📦 <b>Repository:</b> <code>${GITHUB_REPOSITORY}</code>"$'\n'
TEXT+="🌿 <b>Branch:</b> <code>${BRANCH}</code> (${ENV_NAME})"$'\n'
TEXT+="👤 <b>Triggered By:</b> ${ACTOR}"$'\n'
TEXT+="📝 <b>Commit:</b> <code>${COMMIT_HASH}</code> — ${COMMIT_MSG}"$'\n'
TEXT+="${DURATION_LINE%?}"
TEXT+="</blockquote>"

if [ -n "${DEPLOY_URL:-}" ] && [ "$STATUS" = "success" ]; then
  TEXT+=$'\n\n'"🌐 <a href=\"${DEPLOY_URL}\"><b>Visit Deployed Site →</b></a>"
fi

if [ -n "${GITHUB_RUN_ID:-}" ]; then
  TEXT+=$'\n\n'"🔗 <a href=\"${RUN_URL}\"><b>${LINK_TEXT}</b></a>"
fi

RESP=$(curl -s -S -X POST "${API_URL}/sendMessage" \
  --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "parse_mode=HTML" \
  --data-urlencode "disable_web_page_preview=true" \
  "${EXTRA_ARGS[@]}" \
  --data-urlencode "text=${TEXT}" || true)

MSG_ID=$(echo "$RESP" | grep -o '"message_id":[0-9]*' | cut -d: -f2 | head -n 1)
[ -n "$MSG_ID" ] && [ -n "${GITHUB_OUTPUT:-}" ] && echo "message_id=$MSG_ID" >> "$GITHUB_OUTPUT" || true
