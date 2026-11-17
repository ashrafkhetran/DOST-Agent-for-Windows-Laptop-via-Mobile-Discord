# 04 - AI setup
- Subscription (default): `BRAIN=subscription`, run `claude` once and log in. No API key needed.
- API: `BRAIN=api`, set `ANTHROPIC_API_KEY`, `AGENT_MODEL`.
- Voice: `GROQ_API_KEY` (whisper-large-v3, handles Urdu) else local faster-whisper (`WHISPER_MODEL`); replies use edge-tts, or ElevenLabs if keyed.
