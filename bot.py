"""
Telegram Bot for converting university timetables to Ramadan schedules
"""
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

from timetable_extractor import TimetableExtractor
from time_mapper import TimeMapper
from image_generator import TimetableImageGenerator

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class RamadanTimetableBot:
    def __init__(self):
        """Initialize the bot with API keys and modules"""
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if not self.telegram_token or not self.openai_api_key:
            raise ValueError("Missing required environment variables. Check .env file.")
        
        # Initialize modules
        self.extractor = TimetableExtractor(self.openai_api_key)
        self.mapper = TimeMapper('time_mapping.json')
        self.generator = TimetableImageGenerator()
        
        # Create application
        self.application = Application.builder().token(self.telegram_token).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("mappings", self.mappings_command))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_text = """
🌙 مرحباً بك في بوت جدول رمضان
Welcome to Ramadan Timetable Bot!

📸 أرسل صورة جدولك الدراسي وسأقوم بتحويله لأوقات رمضان
Send a photo of your class timetable and I'll convert it to Ramadan times!

📋 الأوامر المتاحة - Available Commands:
/start - عرض هذه الرسالة - Show this message
/help - المساعدة - Get help
/mappings - عرض جدول التحويل - Show time mappings

كيف تستخدم البوت؟
How to use:
1. إلتقط صورة لجدولك الدراسي
   Take a photo of your timetable
2. أرسل الصورة للبوت
   Send the photo to this bot
3. انتظر قليلاً... سأقوم بتحليل الجدول وتحويله
   Wait a moment... I'll analyze and convert it
4. ستستلم جدولك الجديد بأوقات رمضان! 🎉
   You'll receive your new Ramadan timetable! 🎉
"""
        await update.message.reply_text(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
❓ كيف يعمل البوت - How it works:

1️⃣ أرسل صورة واضحة لجدولك الدراسي
   Send a clear photo of your class timetable

2️⃣ تأكد أن الصورة تحتوي على:
   Make sure the image contains:
   • أسماء الأيام (Days of the week)
   • أوقات المحاضرات (Class times)
   • أكواد المواد (Course codes)

3️⃣ البوت سيقوم بـ:
   The bot will:
   ✓ قراءة الجدول - Read the timetable
   ✓ تحويل الأوقات لرمضان - Convert times to Ramadan
   ✓ إنشاء جدول جديد - Generate new timetable
   ✓ إرسال الجدول الجديد لك - Send you the result

⚠️ ملاحظات مهمة - Important notes:
• يجب أن تكون الصورة واضحة
  Image must be clear and readable
• الجدول يجب أن يكون بنفس تنسيق جامعتك
  Timetable must be in your university format
• بعض الأوقات قد لا تكون في جدول التحويل
  Some times might not be in the mapping table

للمساعدة أو الإبلاغ عن مشكلة، تواصل مع المسؤول.
For help or to report issues, contact the admin.
"""
        await update.message.reply_text(help_text)
    
    async def mappings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mappings command - show available time mappings"""
        mappings = self.mapper.get_all_mappings()
        
        text = "📋 جدول تحويل الأوقات - Time Conversion Table\n\n"
        text += "قبل رمضان ← في رمضان\n"
        text += "Before Ramadan ← During Ramadan\n"
        text += "─" * 30 + "\n\n"
        
        for mapping in mappings:
            text += f"{mapping['before_ramadan']} ← {mapping['during_ramadan']}\n"
        
        await update.message.reply_text(text)
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages - main timetable conversion logic"""
        photo_path = None
        output_path = None
        
        try:
            # Send processing message
            processing_msg = await update.message.reply_text(
                "⏳ جاري معالجة الصورة...\nProcessing your timetable...\n\n"
                "1️⃣ استخراج البيانات - Extracting data..."
            )
            
            # Get the photo
            photo = update.message.photo[-1]  # Get highest resolution
            photo_file = await photo.get_file()
            
            # Download photo
            photo_path = f"temp_{update.effective_user.id}.jpg"
            await photo_file.download_to_drive(photo_path)
            
            # Extract timetable data using GPT-4o-mini
            logger.info(f"Extracting timetable for user {update.effective_user.id}")
            classes = self.extractor.extract_from_image(photo_path)
            
            if not classes:
                await processing_msg.edit_text(
                    "❌ عذراً، لم أتمكن من قراءة الجدول\n"
                    "Sorry, I couldn't read the timetable.\n\n"
                    "يرجى التأكد من:\n"
                    "Please make sure:\n"
                    "• الصورة واضحة - Image is clear\n"
                    "• الجدول مرئي بالكامل - Full timetable is visible\n"
                    "• الإضاءة جيدة - Good lighting"
                )
                os.remove(photo_path)
                return
            
            # Update progress
            await processing_msg.edit_text(
                f"⏳ جاري معالجة الصورة...\nProcessing your timetable...\n\n"
                f"✅ استخراج البيانات - Extracting data\n"
                f"   وجدت {len(classes)} محاضرة - Found {len(classes)} classes\n"
                f"2️⃣ تحويل الأوقات - Converting times..."
            )
            
            # Convert times to Ramadan schedule
            logger.info(f"Converting {len(classes)} classes to Ramadan times")
            converted_classes, unmapped = self.mapper.convert_timetable(classes)
            
            if not converted_classes and unmapped:
                await processing_msg.edit_text(
                    "⚠️ لم أتمكن من تحويل أي من المحاضرات\n"
                    "Couldn't convert any classes.\n\n"
                    "الأوقات المستخرجة غير موجودة في جدول التحويل.\n"
                    "The extracted times are not in the mapping table.\n\n"
                    "يرجى التواصل مع المسؤول.\n"
                    "Please contact the admin."
                )
                os.remove(photo_path)
                return
            
            # Update progress
            await processing_msg.edit_text(
                f"⏳ جاري معالجة الصورة...\nProcessing your timetable...\n\n"
                f"✅ استخراج البيانات - Extracting data\n"
                f"✅ تحويل الأوقات - Converting times\n"
                f"   تم تحويل {len(converted_classes)} محاضرة\n"
                f"   Converted {len(converted_classes)} classes\n"
                f"3️⃣ إنشاء الجدول الجديد - Generating new timetable..."
            )
            
            # Generate Ramadan timetable image
            output_path = f"ramadan_timetable_{update.effective_user.id}.png"
            self.generator.generate_timetable(converted_classes, output_path)
            
            # Generate summary text
            summary = self.generator.generate_summary_text(converted_classes, unmapped)
            
            # Send the result
            await processing_msg.edit_text(
                "✅ تم بنجاح! - Done!\n"
                "إرسال الجدول الجديد...\n"
                "Sending your new timetable..."
            )
            
            # Send image
            with open(output_path, 'rb') as img:
                await update.message.reply_photo(
                    photo=img,
                    caption="🌙 جدولك الدراسي بأوقات رمضان\nYour Ramadan Timetable"
                )
            
            # Send summary
            await update.message.reply_text(summary)
            
            # Clean up
            os.remove(photo_path)
            os.remove(output_path)
            await processing_msg.delete()
            
            logger.info(f"Successfully processed timetable for user {update.effective_user.id}")
            
        except Exception as e:
            logger.error(f"Error processing timetable: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ حدث خطأ أثناء المعالجة\n"
                f"An error occurred during processing.\n\n"
                f"الرجاء المحاولة مرة أخرى أو التواصل مع المسؤول.\n"
                f"Please try again or contact the admin.\n\n"
                f"Error: {str(e)}"
            )
            # Clean up on error
            if photo_path and os.path.exists(photo_path):
                os.remove(photo_path)
    
    def run(self):
        """Start the bot"""
        logger.info("Starting Ramadan Timetable Bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point"""
    try:
        bot = RamadanTimetableBot()
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)
        print(f"Error: {e}")
        print("\nPlease make sure:")
        print("1. You have created a .env file with TELEGRAM_BOT_TOKEN and OPENAI_API_KEY")
        print("2. All dependencies are installed (run: pip install -r requirements.txt)")


if __name__ == '__main__':
    main()
