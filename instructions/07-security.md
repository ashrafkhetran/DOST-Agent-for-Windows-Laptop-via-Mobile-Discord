# 07 - Security
- Only `DISCORD_ALLOWED_USER_IDS` may command the agent.
- Secrets only in `.env` (gitignored). Rotate the bot token if it leaks.
- `CONFIRM_RISKY=true`: delete/write/kill/registry/shutdown/services/firewall/etc. need a button approval (`agent/security.py`).
- Every tool call is appended to `.runtime/audit.jsonl` (view with `/audit`).
- No inbound ports are opened (Discord is an outbound connection). Runs as a normal user, not Administrator.
- `/panic` kills the agent immediately. Keep the bot in a private server.
