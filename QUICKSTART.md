# 🚀 Quick Start Guide

## Step 1: Get Your Bot Token

1. Open Telegram
2. Search for **@BotFather**
3. Send `/newbot`
4. Choose a name: `My Ramadan Timetable Bot`
5. Choose a username: `my_ramadan_bot` (must end with 'bot')
6. Copy the token (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

## Step 2: Get Your OpenAI API Key

1. Go to https://platform.openai.com
2. Sign up or log in
3. Click your profile → **View API Keys**
4. Click **Create new secret key**
5. Copy the key (looks like: `sk-...`)
6. **Add credit to your account** (at least $5)

## Step 3: Install Dependencies

```bash
cd ramadan-timetable-bot
pip install -r requirements.txt
```

## Step 4: Configure the Bot

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and paste your credentials:
```
TELEGRAM_BOT_TOKEN=paste_your_bot_token_here
OPENAI_API_KEY=paste_your_openai_key_here
```

## Step 5: Run the Bot

```bash
python bot.py
```

You should see:
```
Starting Ramadan Timetable Bot...
```

## Step 6: Test It!

1. Open Telegram
2. Search for your bot username (e.g., `@my_ramadan_bot`)
3. Send `/start`
4. Send a photo of a timetable
5. Wait a few seconds
6. Receive your Ramadan timetable! 🎉

## Troubleshooting

**"Module not found" error:**
```bash
pip install -r requirements.txt --upgrade
```

**Bot doesn't respond:**
- Check if `python bot.py` is still running
- Verify your bot token is correct
- Make sure you didn't put extra spaces in `.env`

**"Incorrect API key" error:**
- Verify your OpenAI API key
- Make sure you have credits in your OpenAI account
- Check for spaces or typos in `.env`

**Extraction fails:**
- Make sure photo is clear
- Try better lighting
- Ensure full timetable is visible

## Updating Time Mappings

Edit `time_mapping.json`:

```json
{
  "mappings": [
    {
      "before_ramadan": "08:00-09:15",
      "during_ramadan": "10:00-10:50"
    }
  ]
}
```

Restart the bot after updating.

## Need Help?

Check the main [README.md](README.md) for detailed documentation.
