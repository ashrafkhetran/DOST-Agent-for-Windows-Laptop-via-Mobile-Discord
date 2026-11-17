# DOST Agent for Windows via Mobile using Discord

Control your own Windows laptop securely from the Discord mobile app. DOST accepts text or voice instructions, can inspect the screen, work with files and apps, report system health, and reply in English or Urdu.

> This is a customized derivative of [Tanzeel Ur Rehman's Zara AI Laptop Agent](https://github.com/tanzeeldevAi/zara-ai-laptop-agent). The original MIT copyright notice is retained in [LICENSE](LICENSE).

## Features

- Private Discord control restricted to configured user IDs
- Screen capture and visual computer interaction
- File, PowerShell, application, mouse, keyboard, clipboard, and Wi-Fi tools
- English and Urdu voice input/output
- Claude subscription mode or Anthropic API mode
- Optional Groq speech recognition and ElevenLabs voices
- Windows login startup and watchdog recovery
- Optional confirmation before destructive operations

## Requirements

- Windows 10 or 11
- Python 3.10+
- Discord account and private server
- Claude Code subscription login or Anthropic API key

## 1. Download

```powershell
git clone https://github.com/ashrafkhetran/DOST_agent_for_windo_LAPTOP_vis_Mobile_Discord.git
cd DOST_agent_for_windo_LAPTOP_vis_Mobile_Discord
```

## 2. Configure Discord

1. Create an application at <https://discord.com/developers/applications>.
2. Add a bot and enable **Message Content Intent**.
3. Invite it to a private server with these permissions:
   - Send Messages
   - Attach Files
   - Read Message History
   - Embed Links
4. Enable Discord Developer Mode and copy your own User ID.

## 3. Install

Run:

```text
install.bat
```

Add the following private values to `.env`:

```ini
DISCORD_BOT_TOKEN=your_private_bot_token
DISCORD_ALLOWED_USER_IDS=your_discord_user_id
BRAIN=subscription
AGENT_NAME=DOST
```

Never commit or share `.env`.

## 4. Start DOST

Double-click:

```text
START_DOST.bat
```

Then send `/help` or `screenshot my screen` in your private Discord server.

## Optional configuration

- `CONFIRM_RISKY=true` (default) requires a button confirmation in Discord for destructive actions. Every tool call is logged to `.runtime/audit.jsonl`.
- `GROQ_API_KEY` enables faster voice transcription.
- `ELEVENLABS_API_KEY` enables more realistic voice output.
- Run `INSTALL_AUTOSTART.bat` as Administrator for login startup and watchdog recovery.

## Security

This software can control your computer. Use it only on a machine you own, keep the bot in a private server, restrict `DISCORD_ALLOWED_USER_IDS`, protect `.env`, and keep `CONFIRM_RISKY=true` unless you deliberately accept the additional risk.

## Attribution and license

- Original project: [tanzeeldevAi/zara-ai-laptop-agent](https://github.com/tanzeeldevAi/zara-ai-laptop-agent)
- DOST customization: [Ashraf Khetran](https://github.com/ashrafkhetran)
- License: MIT; see [LICENSE](LICENSE)
