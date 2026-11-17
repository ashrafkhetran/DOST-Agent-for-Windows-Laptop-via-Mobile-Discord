# 03 - Discord setup
1. https://discord.com/developers/applications -> New Application -> Bot -> Reset Token (copy to `DISCORD_BOT_TOKEN`).
2. Bot page: enable **Message Content Intent**.
3. OAuth2 -> URL Generator: scope `bot`; permissions Send Messages, Attach Files, Read Message History, Embed Links. Invite to a **private** server (or DM the bot).
4. Discord Settings -> Advanced -> Developer Mode ON; right-click your name -> Copy User ID -> `DISCORD_ALLOWED_USER_IDS`.
Only listed user IDs can command the agent; everyone else is ignored.
