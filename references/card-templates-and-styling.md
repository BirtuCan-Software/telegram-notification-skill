# Message Templates & HTML Styling Guide

This guide documents the complete visual styling, structure, and HTML entity rules used across all deployment and operational Telegram notification cards.

---

## 1. HTML Mode vs MarkdownV2

Telegram Bot API supports `HTML` and `MarkdownV2`. In continuous integration environments, `MarkdownV2` frequently causes parsing failures because real Git commit messages and branch names contain unescaped special characters (e.g., `fix(core): [v1.0] - update auth!`).

With `MarkdownV2`, omitting a backslash before any of the 18 reserved characters (`_`, `*`, `[`, `]`, `(`, `)`, `~`, `\``, `>`, `#`, `+`, `-`, `=`, `|`, `{`, `}`, `.`, `!`) causes Telegram to return HTTP 400: `Bad Request: can't parse entities in message text`.

### The HTML Standard
In `HTML` mode, only 3 characters require escaping:
- `&` $\rightarrow$ `&amp;`
- `<` $\rightarrow$ `&lt;`
- `>` $\rightarrow$ `&gt;`

Our helper script applies this minimal, safe escaping:
```bash
html_escape() {
  printf '%s' "${1:-}" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
}
```

---

## 2. Card Visual Structure

All deployment cards conform to a standardized structure:
1. **Header:** State icon + Bold Title
2. **Body:** Telegram `<blockquote>` containing key metadata in consistent label-value format.
3. **Expandable Details (Optional):** Telegram `<blockquote expandable>` for error stack traces or release notes.
4. **Action Links:** Direct links to GitHub Actions run logs, failure logs, or deployed application.

---

## 3. Official Status Templates

### A. Deployment Started (`action: start`)
```html
🚀 <b>Deployment Started</b>

<blockquote>
📦 <b>Repository:</b> <code>my-org/my-project</code>
🌿 <b>Branch:</b> <code>main</code> (production)
👤 <b>Triggered By:</b> octocat
📝 <b>Commit:</b> <code>a1b2c3d</code> — feat(auth): implement oauth login
</blockquote>

🔗 <a href="https://github.com/my-org/my-project/actions/runs/123456789"><b>View Actions Run #42 →</b></a>
```

### B. Deployment Successful (`action: finish, status: success`)
```html
✅ <b>Deployment Successful</b>

<blockquote>
📦 <b>Repository:</b> <code>my-org/my-project</code>
🌿 <b>Branch:</b> <code>main</code> (production)
👤 <b>Triggered By:</b> octocat
📝 <b>Commit:</b> <code>a1b2c3d</code> — feat(auth): implement oauth login
⏱️ <b>Duration:</b> 1m 45s
</blockquote>

🌐 <a href="https://app.example.com"><b>Visit Deployed Site →</b></a>

🔗 <a href="https://github.com/my-org/my-project/actions/runs/123456789"><b>View Actions Run #42 →</b></a>
```

### C. Deployment Failed with Expandable Details (`status: failure`)
```html
❌ <b>Deployment Failed</b>

<blockquote>
📦 <b>Repository:</b> <code>my-org/my-project</code>
🌿 <b>Branch:</b> <code>main</code> (production)
👤 <b>Triggered By:</b> octocat
📝 <b>Commit:</b> <code>a1b2c3d</code> — feat(auth): implement oauth login
⏱️ <b>Duration:</b> 48s
</blockquote>

<blockquote expandable><b>Details:</b>
<pre><code>TypeError: Cannot read properties of undefined (reading 'token')
  at AuthService.validate (src/auth.ts:42:15)
  at ProcessTicksAndRejections (node:internal/process/task_queues:95:5)</code></pre></blockquote>

🔗 <a href="https://github.com/my-org/my-project/actions/runs/123456789"><b>View Failure Logs #42 →</b></a>
```

### D. Rollback Successful (`status: rollback_success` or `status: rollback`)
```html
🔄 <b>Deployment Rollback Successful</b>

<blockquote>
📦 <b>Repository:</b> <code>my-org/my-project</code>
🌿 <b>Branch:</b> <code>main</code> (production)
👤 <b>Triggered By:</b> octocat
📝 <b>Commit:</b> <code>a1b2c3d</code> — fix(auth): rollback to previous stable commit
⏱️ <b>Duration:</b> 35s
</blockquote>

🔗 <a href="https://github.com/my-org/my-project/actions/runs/123456789"><b>View Actions Run #42 →</b></a>
```

### E. Rollback Failed (`status: rollback_failed`)
```html
🚨 <b>Deployment Rollback Failed</b>

<blockquote>
📦 <b>Repository:</b> <code>my-org/my-project</code>
🌿 <b>Branch:</b> <code>main</code> (production)
👤 <b>Triggered By:</b> octocat
📝 <b>Commit:</b> <code>a1b2c3d</code> — feat: attempt emergency rollback
⏱️ <b>Duration:</b> 52s
</blockquote>

🔗 <a href="https://github.com/my-org/my-project/actions/runs/123456789"><b>View Failure Logs #42 →</b></a>
```

### F. Awaiting Approval (`status: waiting_approval`)
```html
⏳ <b>Deployment Awaiting Approval</b>

<blockquote>
📦 <b>Repository:</b> <code>my-org/my-project</code>
🌿 <b>Branch:</b> <code>main</code> (production)
👤 <b>Triggered By:</b> octocat
📝 <b>Commit:</b> <code>a1b2c3d</code> — feat(checkout): enable new payment gateway
</blockquote>

🔗 <a href="https://github.com/my-org/my-project/actions/runs/123456789"><b>Review Deployment in Actions #42 →</b></a>
```

### G. Completed with Warnings (`status: warning`)
```html
⚠️ <b>Deployment Completed with Warnings</b>

<blockquote>
📦 <b>Repository:</b> <code>my-org/my-project</code>
🌿 <b>Branch:</b> <code>main</code> (production)
👤 <b>Triggered By:</b> octocat
📝 <b>Commit:</b> <code>a1b2c3d</code> — chore: update minor dependencies
⏱️ <b>Duration:</b> 2m 10s
</blockquote>

<blockquote expandable><b>Details:</b>
<pre><code>Warning: Deprecated API version v1alpha used in /api/v1/health
Post-deploy smoke test: 4/5 passed (1 latency warning)</code></pre></blockquote>

🔗 <a href="https://github.com/my-org/my-project/actions/runs/123456789"><b>View Actions Run #42 →</b></a>
```

### H. Release Published (`status: release`)
```html
🏷️ <b>Release Published</b>

<blockquote>
📦 <b>Repository:</b> <code>my-org/my-project</code>
🌿 <b>Branch:</b> <code>v1.2.0</code> (production)
👤 <b>Triggered By:</b> octocat
📝 <b>Commit:</b> <code>a1b2c3d</code> — release: v1.2.0 stable release
</blockquote>

<blockquote expandable><b>Details:</b>
<pre><code>Release Highlights:
- Added OAuth 2.0 PKCE authentication flow
- Reduced bundle size by 18% via tree-shaking
- Fixed session expiration edge case</code></pre></blockquote>

🔗 <a href="https://github.com/my-org/my-project/actions/runs/123456789"><b>View Release in Actions #42 →</b></a>
```

---

## 4. Supported Telegram HTML Tags

The following HTML tags are fully supported by Telegram Bot API:
- `<b>Bold</b>` or `<strong>Bold</strong>`
- `<i>Italic</i>` or `<em>Italic</em>`
- `<code>Inline monospace code</code>`
- `<pre>Monospace block</pre>`
- `<a href="...">Link</a>`
- `<blockquote>Blockquote</blockquote>`
- `<blockquote expandable>Expandable Blockquote</blockquote>`
