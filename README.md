# 🌙 Ramadan Timetable Bot | بوت جدول رمضان

A Telegram bot that automatically converts university class timetables to Ramadan schedules using GPT-4o-mini vision AI.

## Features

- 📸 **Image Recognition**: Upload a photo of your timetable and get automatic extraction
- 🤖 **AI-Powered**: Uses GPT-4o-mini for accurate OCR and data extraction
- 🕌 **Ramadan Time Conversion**: Automatically maps regular class times to Ramadan times
- 🎨 **Visual Output**: Generates a new timetable image with Ramadan times
- 🌐 **Arabic & English**: Supports both languages
- ⚡ **Fast**: Processes timetables in seconds

## How It Works

1. Student sends a photo of their university timetable
2. GPT-4o-mini extracts class information (course codes, days, times)
3. Bot maps each time slot to corresponding Ramadan time
4. Generates a new visual timetable with Ramadan times
5. Sends the converted timetable back to the student

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- OpenAI API Key (from [OpenAI Platform](https://platform.openai.com))

### Installation

1. **Clone or download this project**

```bash
cd ramadan-timetable-bot
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Create environment file**

Create a `.env` file in the project directory:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
```

4. **Update time mappings (if needed)**

Edit `time_mapping.json` to update the time conversion table for your university:

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

### Running the Bot

**Start the bot:**

```bash
python bot.py
```

You should see:
```
Starting Ramadan Timetable Bot...
```

**Keep the bot running** - it needs to stay active to respond to messages.

### Getting Your Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot`
3. Follow the instructions to create your bot
4. Copy the token and paste it in `.env`

### Getting Your OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com)
2. Sign up or log in
3. Go to API Keys section
4. Create a new API key
5. Copy the key and paste it in `.env`

## Usage

### For Students

1. Open Telegram and search for your bot
2. Send `/start` to begin
3. Take a clear photo of your class timetable
4. Send the photo to the bot
5. Wait a few seconds
6. Receive your Ramadan timetable!

### Bot Commands

- `/start` - Start the bot and see welcome message
- `/help` - Get help on how to use the bot
- `/mappings` - View the time conversion table

## Cost Estimate

Using GPT-4o-mini:
- ~$0.01-0.02 per timetable image
- 100 conversions ≈ $1-2
- Very affordable for student use!

## Deployment Options

### Option 1: Run Locally (Simplest)

Just run `python bot.py` on your computer. The bot needs to stay running.

**Pros:**
- Free
- Simple setup
- Full control

**Cons:**
- Computer must stay on
- Not always accessible

### Option 2: Deploy to Cloud (Recommended)

Deploy to a cloud service for 24/7 availability:

**Free Options:**
- [Railway](https://railway.app) - Free tier available
- [Render](https://render.com) - Free tier available
- [PythonAnywhere](https://www.pythonanywhere.com) - Free tier available
- [Fly.io](https://fly.io) - Free tier available

**Paid Options (Cheap):**
- DigitalOcean Droplet ($6/month)
- AWS EC2 t2.micro
- Google Cloud Run

### Deployment Steps (Railway Example)

1. Push code to GitHub
2. Connect GitHub to Railway
3. Add environment variables (TELEGRAM_BOT_TOKEN, OPENAI_API_KEY)
4. Deploy!

## Project Structure

```
ramadan-timetable-bot/
├── bot.py                    # Main bot logic
├── timetable_extractor.py    # GPT-4o-mini extraction
├── time_mapper.py            # Time conversion logic
├── image_generator.py        # Visual timetable generator
├── time_mapping.json         # Time conversion table
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
└── README.md                # This file
```

## Updating Time Mappings

To update the time conversion table:

1. Edit `time_mapping.json`
2. Add/remove/modify mappings
3. Restart the bot

Example:
```json
{
  "before_ramadan": "08:00-09:15",
  "during_ramadan": "10:00-10:50"
}
```

## Troubleshooting

### Bot doesn't respond

- Check if `bot.py` is still running
- Verify your `TELEGRAM_BOT_TOKEN` in `.env`
- Check internet connection

### Can't extract timetable

- Ensure photo is clear and well-lit
- Make sure timetable is fully visible
- Try a different angle/lighting
- Verify your `OPENAI_API_KEY` has credits

### Wrong time conversions

- Check `time_mapping.json` has the correct mappings
- Verify extracted times match your mapping table
- Update mappings if needed

### Import errors

```bash
pip install -r requirements.txt --upgrade
```

## Support

For issues or questions:
- Check the `/help` command in the bot
- Review this README
- Check the logs when running `bot.py`

## License

This project is open source and available for educational purposes.

## Credits

Built with:
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [OpenAI GPT-4o-mini](https://openai.com)
- [Pillow](https://python-pillow.org)

---

Made with ❤️ for university students during Ramadan 🌙
