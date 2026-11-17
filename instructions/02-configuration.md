# 02 - Configuration
All settings live in `.env` (never committed; template is `.env.example`).
Required: `DISCORD_BOT_TOKEN`, `DISCORD_ALLOWED_USER_IDS`.
Brain: `BRAIN=subscription` (Claude Code login) or `BRAIN=api` + `ANTHROPIC_API_KEY`.
Optional: `GROQ_API_KEY` (fast speech-to-text), `ELEVENLABS_API_KEY` (voices), `CONFIRM_RISKY=true` (keep on).
Startup validates `.env` and prints what is missing.
