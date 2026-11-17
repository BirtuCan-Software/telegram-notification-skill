# GitHub Actions Integration Guide

This guide details advanced integration patterns for embedding Telegram deployment, rollback, and release notifications into GitHub Actions pipelines.

---

## 1. Concurrency & Step Ordering

To ensure that notification message IDs are tracked accurately and deployments do not conflict, configure workflow-level concurrency:

```yaml
concurrency:
  group: "deploy-${{ github.ref_name }}"
  cancel-in-progress: false
```

---

## 2. Standard Start-Delete-Replace Deployment Workflow

```yaml
name: Deploy Application

on:
  push:
    branches: [main, staging]
  workflow_dispatch:

concurrency:
  group: "deploy-${{ github.ref_name }}"
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: ⏱️ Start Timer & Notify Telegram
        id: tg_start
        if: env.TELEGRAM_BOT_TOKEN != '' && env.TELEGRAM_CHAT_ID != ''
        uses: BirtuCan-Software/telegram-notification-skill@v1
        with:
          bot_token: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          chat_id: ${{ secrets.TELEGRAM_CHAT_ID }}
          message_thread_id: ${{ secrets.TELEGRAM_MESSAGE_THREAD_ID }}
          action: start

      - name: 📥 Checkout Code
        uses: actions/checkout@v4

      - name: 📦 Install & Build
        run: |
          npm ci
          npm run build

      - name: 🚀 Deploy Application
        run: |
          echo "Deploying application..."

      - name: 🔔 Notify Telegram Final Status
        if: always() && env.TELEGRAM_BOT_TOKEN != '' && env.TELEGRAM_CHAT_ID != ''
        uses: BirtuCan-Software/telegram-notification-skill@v1
        with:
          bot_token: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          chat_id: ${{ secrets.TELEGRAM_CHAT_ID }}
          message_thread_id: ${{ secrets.TELEGRAM_MESSAGE_THREAD_ID }}
          action: finish
          status: ${{ job.status }}
          start_message_id: ${{ steps.tg_start.outputs.message_id }}
          start_time: ${{ steps.tg_start.outputs.start_time }}
          deploy_url: ${{ vars.DEPLOY_URL }}
```

---

## 3. Rollback Notification Pattern

When a deployment step fails and an automated rollback step restores the previous release, report the rollback outcome accurately:

```yaml
      - name: 🔄 Execute Automated Rollback
        if: failure()
        id: rollback
        run: |
          echo "Restoring previous release..."
          # execute rollback script

      - name: 🔔 Notify Rollback Succeeded
        if: failure() && steps.rollback.outcome == 'success'
        uses: BirtuCan-Software/telegram-notification-skill@v1
        with:
          bot_token: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          chat_id: ${{ secrets.TELEGRAM_CHAT_ID }}
          action: finish
          status: rollback_success
          start_message_id: ${{ steps.tg_start.outputs.message_id }}
          start_time: ${{ steps.tg_start.outputs.start_time }}
          details: "Automated rollback restored previous release without downtime."

      - name: 🚨 Notify Rollback Failed
        if: failure() && steps.rollback.outcome == 'failure'
        uses: BirtuCan-Software/telegram-notification-skill@v1
        with:
          bot_token: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          chat_id: ${{ secrets.TELEGRAM_CHAT_ID }}
          action: finish
          status: rollback_failed
          start_message_id: ${{ steps.tg_start.outputs.message_id }}
          start_time: ${{ steps.tg_start.outputs.start_time }}
          details: "CRITICAL: Automated rollback failed. Manual intervention required."
```

---

## 4. Standalone Release Announcement (`action: notify`)

For tagged releases or manual broadcasts, send a standalone card without needing a prior `start` step:

```yaml
name: Publish Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: 🏷️ Announce Release in Telegram
        uses: BirtuCan-Software/telegram-notification-skill@v1
        with:
          bot_token: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          chat_id: ${{ secrets.TELEGRAM_CHAT_ID }}
          action: notify
          status: release
          custom_title: "Product Release"
          details: ${{ github.event.head_commit.message }}
```

---

## 5. Silent Background Checks (`silent: true`)

For nighttime cron jobs, staging smoke tests, or database backups where sound/vibration alerts should be suppressed:

```yaml
      - name: 🔔 Silent Telegram Status
        uses: BirtuCan-Software/telegram-notification-skill@v1
        with:
          bot_token: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          chat_id: ${{ secrets.TELEGRAM_CHAT_ID }}
          action: notify
          status: success
          custom_title: "Database Backup"
          silent: "true"
```
