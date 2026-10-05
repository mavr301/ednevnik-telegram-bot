<p align="center"><img src="avatar.png" width="160" alt="School bot"></p>

# School Bot — e-Dnevnik grades in Telegram

A small Telegram bot that logs in to the Croatian e-Dnevnik parent/student portal
([ocjene.skole.hr](https://ocjene.skole.hr)), checks for new marks once a day and posts them
to a Telegram chat. You can also ask it for all marks, a single subject, or averages.

> **Unofficial.** This project is not affiliated with CARNet or the Ministry of Science and
> Education. It scrapes the web portal, so it can break whenever the portal's layout changes.

## Features

- 📬 Daily check at a configurable time — new marks and teacher notes are sent to your chat
- 📚 `/all` — every mark, one message per subject, with averages
- 🔎 `/subject <name>` — marks for one subject (partial, case-insensitive match)
- 📋 `/subjects` — pick a subject from buttons
- 📊 `/avg` — average per subject, best first
- 🆕 `/marks` — check right now for marks added since the last check
- 🔒 Restrict the bot to specific Telegram users

## ⚠️ Requirement: a Croatian IP address

CARNet blocks logins from non-Croatian IP addresses. The bot **must run from a machine with a
Croatian IP**: a home server / Raspberry Pi / NAS, your own PC, or a VPS hosted in Croatia.
A typical cloud VPS in Germany or Finland will fail with a login or connection error.

## Setup

### 1. Create a Telegram bot

1. Open [@BotFather](https://t.me/BotFather), send `/newbot` and follow the prompts.
2. Copy the token it gives you → `TELEGRAM_BOT_TOKEN`.
3. Optional: `/setuserpic` with [avatar.png](avatar.png), and `/setcommands` with:
   ```
   marks - Check for new marks now
   all - All marks by subject
   subjects - Pick a subject
   subject - Marks for one subject
   avg - Averages per subject
   ```

### 2. Find your IDs

- **Your user ID** (`ALLOWED_USER_IDS`): message [@userinfobot](https://t.me/userinfobot).
- **Chat ID** (`TELEGRAM_CHAT_ID`) — where daily updates go:
  - private chat with the bot: same as your user ID (send the bot `/start` first);
  - group: add the bot to the group, send a message, then open
    `https://api.telegram.org/bot<TOKEN>/getUpdates` and look for `"chat":{"id":-100...}`.

### 3. Configure

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | yes | Token from BotFather |
| `EDNEVNIK_USERNAME` | yes | AAI@EduHr login, e.g. `ime.prezime@skole.hr` |
| `EDNEVNIK_PASSWORD` | yes | AAI@EduHr password |
| `TELEGRAM_CHAT_ID` | no | Chat for daily updates. If empty, the daily check is disabled |
| `ALLOWED_USER_IDS` | recommended | Comma-separated Telegram user IDs allowed to use commands. **If empty, anyone who finds the bot can read the grades.** |
| `DAILY_CHECK_TIME` | no | `HH:MM`, default `08:00` |
| `TIMEZONE` | no | Default `Europe/Zagreb` |
| `STORAGE_FILE` | no | Where seen marks are stored, default `data/grades.json` |
| `SAVE_DEBUG_HTML` | no | Set to `1` to save the raw grades page for troubleshooting |

Accounts with mToken / two-factor login are not supported.

### 4. Run

**Docker Compose (recommended)**

```bash
docker compose up -d
```

This pulls the published image `ghcr.io/mavr301/school-bot:latest`. To build from source
instead, swap `image:` for `build: .` in [docker-compose.yml](docker-compose.yml).
The `./data` folder keeps track of which marks were already reported — keep it between restarts.

**Plain Docker**

```bash
docker run -d --name school-bot --env-file .env -v "$PWD/data:/app/data" --restart unless-stopped ghcr.io/mavr301/school-bot:latest
```

**Without Docker** (Python 3.10+)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**Coolify / other PaaS:** deploy the image (or this repo with the Dockerfile), set the
variables above in the UI and mount a persistent volume at `/app/data`. Remember the
Croatian-IP requirement for the server.

On the first daily run the bot sends all existing marks once; after that only new ones.

## Updating

```bash
docker compose pull && docker compose up -d
```

Image tags: `latest` = newest release, `1.2.3` / `1.2` = specific release, `edge` = current
`master` (may be unstable). See [Releases](https://github.com/mavr301/school-bot/releases)
for what changed.

## Troubleshooting

- **Login failed / timeout** — check credentials, then check the server's IP is Croatian.
- **"No grade tables found" in logs, or marks missing** — the portal layout probably changed.
  Set `SAVE_DEBUG_HTML=1`, restart, run `/all`, and look at `data/debug_grades.html`.
  When opening an issue, attach it **with names and grades blanked out**.
- **Bot doesn't answer** — your ID isn't in `ALLOWED_USER_IDS`, or another instance is
  running with the same token.

## Contributing

Bug reports and pull requests are welcome. Please never paste passwords, tokens or your
child's personal data into issues.

## License

[MIT](LICENSE)
