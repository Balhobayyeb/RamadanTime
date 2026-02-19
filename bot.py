"""
Telegram Bot for converting university timetables to Ramadan schedules
"""

import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from dotenv import load_dotenv

from timetable_extractor import TimetableExtractor
from time_mapper import TimeMapper
from image_generator import TimetableImageGenerator
from extraction_logger import ExtractionLogger

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class RamadanTimetableBot:
    def __init__(self):
        """Initialize the bot with API keys and modules"""
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        if not self.telegram_token or not self.openai_api_key:
            raise ValueError("Missing required environment variables. Check .env file.")

        # Initialize modules
        self.extractor = TimetableExtractor(self.openai_api_key)
        self.mapper = TimeMapper("time_mapping.json")
        self.generator = TimetableImageGenerator()
        self.extraction_logger = ExtractionLogger()

        # Create application
        self.application = Application.builder().token(self.telegram_token).build()

        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("mappings", self.mappings_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_text = (
            "مرحبا بك في بوت جدول رمضان\n"
            "Welcome to Ramadan Timetable Bot!\n\n"
            "أرسل صورة جدولك الدراسي وسأقوم بتحويله لأوقات رمضان\n"
            "Send a photo of your class timetable and I'll convert it to Ramadan times!\n\n"
            "الأوامر المتاحة - Available Commands:\n"
            "/start - عرض هذه الرسالة\n"
            "/help - المساعدة\n"
            "/mappings - عرض جدول التحويل\n"
            "/stats - إحصائيات البوت\n\n"
            "كيف تستخدم البوت؟\n"
            "1. إلتقط صورة لجدولك الدراسي\n"
            "2. أرسل الصورة للبوت\n"
            "3. انتظر قليلا... سأقوم بتحليل الجدول وتحويله\n"
            "4. ستستلم جدولك الجديد بأوقات رمضان!"
        )
        await update.message.reply_text(welcome_text)  # type: ignore[union-attr]

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "كيف يعمل البوت - How it works:\n\n"
            "1. أرسل صورة واضحة لجدولك الدراسي\n"
            "   Send a clear photo of your class timetable\n\n"
            "2. تأكد أن الصورة تحتوي على:\n"
            "   - أسماء الأيام (Days of the week)\n"
            "   - أوقات المحاضرات (Class times)\n"
            "   - أكواد المواد (Course codes)\n\n"
            "3. البوت سيقوم بـ:\n"
            "   - قراءة الجدول باستخدام GPT-4o\n"
            "   - تحويل الأوقات لرمضان\n"
            "   - إنشاء جدول جديد\n"
            "   - إرسال الجدول الجديد لك\n\n"
            "ملاحظات مهمة:\n"
            "- يجب أن تكون الصورة واضحة\n"
            "- الجدول يجب أن يكون بنفس تنسيق جامعتك\n"
            "- بعض الأوقات قد لا تكون في جدول التحويل\n"
            "- البوت يحاول عدة مرات للحصول على أفضل نتيجة\n\n"
            "للمساعدة أو الإبلاغ عن مشكلة، تواصل مع المسؤول."
        )
        await update.message.reply_text(help_text)  # type: ignore[union-attr]

    async def mappings_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /mappings command - show available time mappings"""
        mappings = self.mapper.get_all_mappings()

        text = "جدول تحويل الأوقات - Time Conversion Table\n\n"
        text += "قبل رمضان -> في رمضان\n"
        text += "-" * 30 + "\n\n"

        for mapping in mappings:
            text += f"{mapping['before_ramadan']} -> {mapping['during_ramadan']}\n"

        await update.message.reply_text(text)  # type: ignore[union-attr]

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command - show bot statistics"""
        stats = self.extraction_logger.get_stats()

        text = (
            "احصائيات البوت - Bot Statistics\n\n"
            f"عدد المحاولات: {stats['total_attempts']}\n"
            f"نجحت: {stats['successful_attempts']}\n"
            f"فشلت: {stats['failed_attempts']}\n"
            f"نسبة النجاح: {stats['success_rate']:.1f}%\n"
            f"متوسط المحاضرات المستخرجة: {stats['average_classes_extracted']:.1f}\n"
        )
        await update.message.reply_text(text)  # type: ignore[union-attr]

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages - main timetable conversion logic"""
        photo_path = None
        output_path = None
        user_id = update.effective_user.id if update.effective_user else 0
        message = update.message
        if message is None:
            return

        try:
            # Send processing message
            processing_msg = await message.reply_text(
                "جاري معالجة الصورة...\n"
                "Processing your timetable...\n\n"
                "1. استخراج البيانات باستخدام GPT-4o..."
            )

            # Get the photo
            photo = message.photo[-1]  # Get highest resolution
            photo_file = await photo.get_file()

            # Download photo
            photo_path = f"temp_{user_id}.jpg"
            await photo_file.download_to_drive(photo_path)

            # Extract timetable data using GPT-4o with retry logic
            logger.info(f"Extracting timetable for user {user_id}")
            classes = self.extractor.extract_from_image(photo_path, user_id=user_id)

            if not classes:
                await processing_msg.edit_text(
                    "عذرا، لم أتمكن من قراءة الجدول\n"
                    "Sorry, I couldn't read the timetable.\n\n"
                    "يرجى التأكد من:\n"
                    "- الصورة واضحة وليست مقصوصة\n"
                    "- الجدول مرئي بالكامل\n"
                    "- الإضاءة جيدة\n"
                    "- لا توجد انعكاسات على الشاشة\n\n"
                    "حاول إرسال الصورة مرة أخرى أو التقاط صورة جديدة."
                )
                if photo_path and os.path.exists(photo_path):
                    os.remove(photo_path)
                return

            # Update progress
            await processing_msg.edit_text(
                "جاري معالجة الصورة...\n"
                "Processing your timetable...\n\n"
                f"تم استخراج البيانات - وجدت {len(classes)} محاضرة\n"
                f"Found {len(classes)} classes\n"
                "2. تحويل الأوقات لرمضان..."
            )

            # Convert times to Ramadan schedule
            logger.info(f"Converting {len(classes)} classes to Ramadan times")
            converted_classes, unmapped = self.mapper.convert_timetable(classes)

            # Log conversion results
            unmapped_times = [
                f"{c.get('course_code', '?')}: {c['start_time']}-{c['end_time']}"
                for c in unmapped
            ]
            self.extraction_logger.log_conversion_result(
                user_id=user_id,
                extracted_count=len(classes),
                converted_count=len(converted_classes),
                unmapped_count=len(unmapped),
                unmapped_times=unmapped_times,
            )

            if not converted_classes and unmapped:
                # Build detailed error message with suggestions
                error_text = (
                    "لم أتمكن من تحويل أي من المحاضرات\n"
                    "Couldn't convert any classes.\n\n"
                    "الأوقات المستخرجة غير موجودة في جدول التحويل:\n"
                )
                for cls in unmapped:
                    time_slot = f"{cls['start_time']}-{cls['end_time']}"
                    error_text += f"  {cls.get('course_code', '?')}: {time_slot}\n"

                    # Show closest suggestions
                    suggestions = self.mapper.get_unmapped_suggestions(
                        cls["start_time"], cls["end_time"]
                    )
                    if suggestions:
                        closest = suggestions[0]
                        error_text += f"    أقرب وقت: {closest['before_ramadan']}\n"

                error_text += (
                    "\nيرجى التأكد من أن الصورة واضحة أو التواصل مع المسؤول.\n"
                    "Please make sure the image is clear or contact the admin."
                )
                await processing_msg.edit_text(error_text)
                if photo_path and os.path.exists(photo_path):
                    os.remove(photo_path)
                return

            # Update progress
            fuzzy_count = sum(
                1 for c in converted_classes if c.get("match_type") == "fuzzy"
            )
            progress_text = (
                "جاري معالجة الصورة...\n"
                "Processing your timetable...\n\n"
                "تم استخراج البيانات\n"
                f"تم تحويل {len(converted_classes)} محاضرة\n"
                f"Converted {len(converted_classes)} classes\n"
            )
            if fuzzy_count > 0:
                progress_text += f"   ({fuzzy_count} تقريبي - fuzzy matched)\n"
            if unmapped:
                progress_text += f"   ({len(unmapped)} لم يتم تحويلها)\n"
            progress_text += "3. إنشاء الجدول الجديد..."

            await processing_msg.edit_text(progress_text)

            # Generate Ramadan timetable image
            output_path = f"ramadan_timetable_{user_id}.png"
            self.generator.generate_timetable(converted_classes, output_path)

            # Generate summary text
            summary = self.generator.generate_summary_text(converted_classes, unmapped)

            # Send the result
            await processing_msg.edit_text("تم بنجاح! - Done!\nإرسال الجدول الجديد...")

            # Send image
            with open(output_path, "rb") as img:
                await message.reply_photo(
                    photo=img,
                    caption="جدولك الدراسي بأوقات رمضان\nYour Ramadan Timetable",
                )

            # Send summary
            await message.reply_text(summary)

            # Clean up
            if photo_path and os.path.exists(photo_path):
                os.remove(photo_path)
            if output_path and os.path.exists(output_path):
                os.remove(output_path)
            await processing_msg.delete()

            logger.info(f"Successfully processed timetable for user {user_id}")

        except Exception as e:
            logger.error(f"Error processing timetable: {e}", exc_info=True)
            try:
                await message.reply_text(
                    "حدث خطأ أثناء المعالجة\n"
                    "An error occurred during processing.\n\n"
                    "الرجاء المحاولة مرة أخرى أو التواصل مع المسؤول.\n"
                    "Please try again or contact the admin.\n\n"
                    f"Error: {str(e)}"
                )
            except Exception:
                logger.error("Failed to send error message to user")
            # Clean up on error
            if photo_path and os.path.exists(photo_path):
                os.remove(photo_path)
            if output_path and os.path.exists(output_path):
                os.remove(output_path)

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
        print(
            "1. You have created a .env file with TELEGRAM_BOT_TOKEN and OPENAI_API_KEY"
        )
        print(
            "2. All dependencies are installed (run: pip install -r requirements.txt)"
        )


if __name__ == "__main__":
    main()
