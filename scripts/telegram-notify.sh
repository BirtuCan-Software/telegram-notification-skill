#!/usr/bin/env bash
# ==============================================================================
# Script: telegram-notify.sh
# Purpose: Orchestrates atomic Start-Delete-Replace and standalone CI/CD deployment
#          notifications via the Telegram Bot API with clean HTML card formatting.
# Compatibility: POSIX bash, curl. Non-blocking (never breaks CI pipelines on failure).
# ==============================================================================

set -uo pipefail

ACTION="${1:-}"

# Strict HTML escaping function: handles &, <, >
html_escape() {
  printf '%s' "${1:-}" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
}

# Helper: Build expandable details section if provided
build_details_block() {
  local raw_input="$1"
  if [ -n "$raw_input" ]; then
    local escaped_details
    escaped_details=$(printf '%s' "$raw_input" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g')
    printf '\n\n<blockquote expandable><b>Details:</b>\n<pre><code>%s</code></pre></blockquote>' "$escaped_details"
  fi
}

# Helper: Resolve icon, title, and link text for any status
resolve_status_meta() {
  local status="$1"
  local default_title="${TITLE_PREFIX:-Deployment}"
  case "$status" in
    success)
      ICON="✅"; HEADER="${ICON} <b>${default_title} Successful</b>"
      LINK_TEXT="View Actions Run #${RUN_NUM:-1} →" ;;
    failure)
      ICON="❌"; HEADER="${ICON} <b>${default_title} Failed</b>"
      LINK_TEXT="View Failure Logs #${RUN_NUM:-1} →" ;;
    cancelled)
      ICON="⚠️"; HEADER="${ICON} <b>${default_title} Cancelled</b>"
      LINK_TEXT="View Actions Run #${RUN_NUM:-1} →" ;;
    rollback|rollback_success)
      ICON="🔄"; HEADER="${ICON} <b>${default_title} Rollback Successful</b>"
      LINK_TEXT="View Actions Run #${RUN_NUM:-1} →" ;;
    rollback_failed)
      ICON="🚨"; HEADER="${ICON} <b>${default_title} Rollback Failed</b>"
      LINK_TEXT="View Failure Logs #${RUN_NUM:-1} →" ;;
    waiting_approval|approval_required)
      ICON="⏳"; HEADER="${ICON} <b>${default_title} Awaiting Approval</b>"
      LINK_TEXT="Review Deployment in Actions #${RUN_NUM:-1} →" ;;
    warning)
      ICON="⚠️"; HEADER="${ICON} <b>${default_title} Completed with Warnings</b>"
      LINK_TEXT="View Actions Run #${RUN_NUM:-1} →" ;;
    release)
      ICON="🏷️"; HEADER="${ICON} <b>${TITLE_PREFIX:-Release} Published</b>"
      LINK_TEXT="View Release in Actions #${RUN_NUM:-1} →" ;;
    *)
      ICON="ℹ️"; HEADER="${ICON} <b>${default_title} ${status}</b>"
      LINK_TEXT="View Actions Run #${RUN_NUM:-1} →" ;;
  esac
}

# Helper: Calculate formatted execution duration
calculate_duration() {
  local st="${1:-${DEPLOY_START_TIME:-}}"
  if [ -n "$st" ]; then
    if [[ "$st" =~ ^[0-9]+$ ]] && [ "$st" -gt 1000000000 ]; then
      local elapsed=$(( $(date +%s) - st ))
      local mins=$(( elapsed / 60 ))
      local secs=$(( elapsed % 60 ))
      if [ $mins -gt 0 ]; then
        printf '⏱️ <b>Duration:</b> %dm %ds\n' "$mins" "$secs"
      else
        printf '⏱️ <b>Duration:</b> %ds\n' "$secs"
      fi
    else
      printf '⏱️ <b>Duration:</b> %s\n' "$st"
    fi
  fi
}

# Helper: Build unified metadata blockquote
build_blockquote() {
  local duration="${1:-}"
  local bq="<blockquote>"
  bq+="📦 <b>Repository:</b> <code>${REPO}</code>"$'\n'
  bq+="🌿 <b>Branch:</b> <code>${BRANCH}</code> (${ENV_NAME})"$'\n'
  bq+="👤 <b>Triggered By:</b> ${ACTOR}"$'\n'
  bq+="📝 <b>Commit:</b> <code>${COMMIT_HASH}</code> — ${COMMIT_MSG_ESCAPED}"
  if [ -n "$duration" ]; then
    bq+=$'\n'"${duration%?}"
  fi
  bq+="</blockquote>"
  echo "$bq"
}

# Helper: Compose complete Telegram HTML card
compose_card() {
  local header="$1"
  local duration="$2"
  local status="$3"
  local link_text="$4"

  local msg="${header}"$'\n\n'
  msg+=$(build_blockquote "$duration")
  msg+=$(build_details_block "$RAW_DETAILS")

  if [ -n "$DEPLOY_TARGET_URL" ] && [ "$status" = "success" ]; then
    msg+=$'\n\n'"🌐 <a href=\"${DEPLOY_TARGET_URL}\"><b>Visit Deployed Site →</b></a>"
  fi

  if [ -n "$RUN_ID" ] && [ -n "$link_text" ]; then
    msg+=$'\n\n'"🔗 <a href=\"${RUN_URL}\"><b>${link_text}</b></a>"
  fi

  echo "$msg"
}

# If sourced for functions only, return cleanly
if [ "$ACTION" = "__source__" ]; then
  return 0 2>/dev/null || exit 0
fi

BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHAT_ID="${TELEGRAM_CHAT_ID:-}"
RAW_THREAD_ID="${TELEGRAM_MESSAGE_THREAD_ID:-}"

# Guard: If Telegram credentials are missing, log gracefully and exit 0
if [ -z "$BOT_TOKEN" ] || [ -z "$CHAT_ID" ]; then
  echo "⚠️ Telegram secrets (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID) not configured. Skipping notification."
  exit 0
fi

API_URL="https://api.telegram.org/bot${BOT_TOKEN}"

# Context variables with safe fallbacks matching standard CI/CD conventions
REPO=$(html_escape "${GITHUB_REPOSITORY:-local/repo}")
BRANCH=$(html_escape "${GITHUB_REF_NAME:-main}")
ENV_NAME="${GITHUB_ENVIRONMENT:-${ENVIRONMENT_NAME:-}}"
if [ -z "$ENV_NAME" ]; then
  [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ] && ENV_NAME="production" || ENV_NAME="${BRANCH}"
fi

ACTOR=$(html_escape "${GITHUB_TRIGGERING_ACTOR:-${GITHUB_ACTOR:-developer}}")
SERVER_URL="${GITHUB_SERVER_URL:-https://github.com}"
REPO_NAME="${GITHUB_REPOSITORY:-local/repo}"
RUN_ID="${GITHUB_RUN_ID:-}"
RUN_NUM="${GITHUB_RUN_NUMBER:-1}"
RUN_URL="${SERVER_URL}/${REPO_NAME}/actions/runs/${RUN_ID}"

COMMIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "${GITHUB_SHA:0:7}")
RAW_COMMIT_MSG="${COMMIT_MESSAGE:-$(git log -1 --pretty=format:'%s' 2>/dev/null || echo 'Manual Trigger')}"
COMMIT_MSG_ESCAPED=$(echo "$RAW_COMMIT_MSG" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')

TITLE_PREFIX="${NOTIFICATION_TITLE:-}"
DEPLOY_TARGET_URL="${DEPLOY_URL:-${APP_URL:-${CPANEL_FRONTEND_DOMAIN:-}}}"
RAW_DETAILS="${NOTIFICATION_DETAILS:-${DETAILS:-}}"
SILENT_MODE="${NOTIFICATION_SILENT:-${SILENT:-false}}"

# Sanitize Thread ID & extra args
THREAD_ID=$(echo "$RAW_THREAD_ID" | tr -d '[:space:]')
EXTRA_ARGS=()
[ -n "$THREAD_ID" ] && [ "$THREAD_ID" != "0" ] && EXTRA_ARGS+=(--data-urlencode "message_thread_id=${THREAD_ID}")
[ "$SILENT_MODE" = "true" ] || [ "$SILENT_MODE" = "1" ] && EXTRA_ARGS+=(--data-urlencode "disable_notification=true")

# Helper: Send message using curl with --data-urlencode
send_telegram_msg() {
  local msg_text="$1"
  curl -s -S -X POST "${API_URL}/sendMessage" \
    --data-urlencode "chat_id=${CHAT_ID}" \
    --data-urlencode "parse_mode=HTML" \
    --data-urlencode "disable_web_page_preview=true" \
    "${EXTRA_ARGS[@]}" \
    --data-urlencode "text=${msg_text}" || true
}

# Helper: Delete message using curl
delete_telegram_msg() {
  local msg_id="$1"
  if [ -n "$msg_id" ] && [ "$msg_id" != "0" ] && [ "$msg_id" != "null" ]; then
    curl -s -S -X POST "${API_URL}/deleteMessage" \
      --data-urlencode "chat_id=${CHAT_ID}" \
      --data-urlencode "message_id=${msg_id}" >/dev/null 2>&1 || true
  fi
}

case "$ACTION" in
  start)
    HEADER="🚀 <b>${TITLE_PREFIX:-Deployment} Started</b>"
    MESSAGE=$(compose_card "$HEADER" "" "start" "View Actions Run #${RUN_NUM} →")
    RESP=$(send_telegram_msg "$MESSAGE")
    MSG_ID=$(echo "$RESP" | grep -o '"message_id":[0-9]*' | cut -d: -f2 | head -n 1)

    if [ -n "$MSG_ID" ]; then
      echo "TELEGRAM_STARTED_MSG_ID=$MSG_ID"
      [ -n "${GITHUB_ENV:-}" ] && echo "TELEGRAM_STARTED_MSG_ID=$MSG_ID" >> "$GITHUB_ENV"
      [ -n "${GITHUB_OUTPUT:-}" ] && echo "message_id=$MSG_ID" >> "$GITHUB_OUTPUT"
    fi

    NOW_TS=$(date +%s)
    [ -n "${GITHUB_ENV:-}" ] && echo "DEPLOY_START_TIME=$NOW_TS" >> "$GITHUB_ENV"
    [ -n "${GITHUB_OUTPUT:-}" ] && echo "start_time=$NOW_TS" >> "$GITHUB_OUTPUT"
    ;;

  finish)
    STATUS="${2:-success}"
    STARTED_MSG_ID="${3:-${START_MSG_ID:-${TELEGRAM_STARTED_MSG_ID:-}}}"
    START_TIME="${4:-${DEPLOY_START_TIME:-}}"

    # 1. Delete previous 'Started' notification to keep topic zero-clutter
    [ -n "$STARTED_MSG_ID" ] && delete_telegram_msg "$STARTED_MSG_ID"

    # 2. Duration & Card Assembly
    DURATION_LINE=$(calculate_duration "$START_TIME")
    resolve_status_meta "$STATUS"
    MESSAGE=$(compose_card "$HEADER" "$DURATION_LINE" "$STATUS" "$LINK_TEXT")

    RESP=$(send_telegram_msg "$MESSAGE")
    MSG_ID=$(echo "$RESP" | grep -o '"message_id":[0-9]*' | cut -d: -f2 | head -n 1)
    [ -n "$MSG_ID" ] && [ -n "${GITHUB_OUTPUT:-}" ] && echo "message_id=$MSG_ID" >> "$GITHUB_OUTPUT"
    echo "Final notification ($STATUS) sent."
    ;;

  notify)
    STATUS="${2:-info}"
    resolve_status_meta "$STATUS"
    MESSAGE=$(compose_card "$HEADER" "" "$STATUS" "$LINK_TEXT")

    RESP=$(send_telegram_msg "$MESSAGE")
    MSG_ID=$(echo "$RESP" | grep -o '"message_id":[0-9]*' | cut -d: -f2 | head -n 1)
    [ -n "$MSG_ID" ] && [ -n "${GITHUB_OUTPUT:-}" ] && echo "message_id=$MSG_ID" >> "$GITHUB_OUTPUT"
    echo "Standalone notification ($STATUS) sent."
    ;;

  delete)
    MSG_ID="${2:-}"
    delete_telegram_msg "$MSG_ID"
    echo "Notification ($MSG_ID) deleted."
    ;;

  *)
    echo "Usage: $0 {start|finish [status] [started_msg_id] [start_time]|notify [status]|delete [msg_id]}"
    exit 1
    ;;
esac

exit 0
