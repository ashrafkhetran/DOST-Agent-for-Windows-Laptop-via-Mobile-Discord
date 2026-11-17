# 09 - Troubleshooting
- "Setup incomplete": fill the listed `.env` values.
- Bot online but silent: enable Message Content Intent; check your user ID is in `DISCORD_ALLOWED_USER_IDS`.
- ModuleNotFoundError: `.venv\Scripts\python.exe -m pip install -r requirements.txt`.
- Subscription brain fails: run `claude` in a terminal and log in again.
- Voice not understood: set `GROQ_API_KEY`; local model is slow on weak CPUs.
- Logs/screenshots: `.runtime\`.
