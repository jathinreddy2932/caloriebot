import asyncio
import json
import logging
from datetime import date
from telegram import Update, BotCommand
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from app.config import settings
from app.database import SessionLocal
from app.models import MealLog, DailyReport
from app.gemini_parser import parse_food_with_gemini, detect_meal_reference, extract_meal_type_heuristic
from app.report_generator import (
    analyze_day_meals,
    format_telegram_eod_report,
    generate_pdf_report
)

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or settings.USER_NAME
    msg = (
        f"👋 *Welcome {user_name}! I am your personal Calorie & Nutrition Coach.*\n\n"
        f"🎯 *Your Fat-Loss Cut Profile:*\n"
        f"• Current Weight: `{settings.USER_CURRENT_WEIGHT_KG} kg`\n"
        f"• Target Goal: `{settings.USER_TARGET_WEIGHT_KG} kg` (Drop -19 kg)\n"
        f"• Height & Age: `{int(settings.USER_HEIGHT_CM)} cm`, `{settings.USER_AGE} y/o male`\n"
        f"• Daily Budget: *{settings.DAILY_CALORIE_BUDGET} kcal* (~500 kcal safe deficit)\n"
        f"• Protein Target: *{settings.DAILY_PROTEIN_TARGET_G}g*\n\n"
        f"💬 *How to log meals:*\n"
        f"Just text me anytime what you ate, for example:\n"
        f"👉 _'for morning/breakfast i ate 2 dosas and sambar'_\n"
        f"👉 _'for lunch i ate 1 bowl rice, dal and chicken curry'_\n"
        f"👉 _'for snack i had samosa and chai'_\n"
        f"👉 _'meanwhile i ate an apple and almonds'_\n"
        f"👉 _'for dinner i ate 2 rotis with paneer'_\n\n"
        f"🏁 *When finished for the day:*\n"
        f"Type *EOD* to receive your complete Daily Audit + Excess Analysis + PDF Report!\n\n"
        f"📌 *Other Commands:*\n"
        f"/status — See today's running intake\n"
        f"/eod — Generate daily report\n"
        f"/undo — Delete last logged meal\n"
        f"/dashboard — Web app link"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "💡 *CalorieBot Quick Guide*\n\n"
        "1. *Log meals naturally:*\n"
        "• 'for breakfast / tiffin i ate 3 idlis with chutney'\n"
        "• 'for lunch i ate rice, chicken curry and curd'\n"
        "• 'for snacks i ate biscuits and milk tea'\n"
        "• 'meanwhile i ate a banana'\n"
        "• 'for dinner i ate 2 chapatis and dal'\n\n"
        "2. *End of Day Report:*\n"
        "Send *EOD* anytime at night to get your full calorie audit, what excess you ate, what to control tomorrow, and an instant PDF report.\n\n"
        "3. *Commands:*\n"
        "/status — Today's totals & remaining calories\n"
        "/eod — Trigger EOD report immediately\n"
        "/undo — Remove your last meal log\n"
        "/dashboard — Open the live web analytics dashboard"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = date.today()
    db = SessionLocal()
    try:
        meals = db.query(MealLog).filter(MealLog.date == today).order_by(MealLog.created_at.asc()).all()
        if not meals:
            await update.message.reply_text(
                f"ℹ️ No meals logged yet for today ({today.strftime('%d %b')}).\n"
                f"Send me your breakfast or snack to get started! Budget: *{settings.DAILY_CALORIE_BUDGET} kcal*",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        total_cals = sum(m.total_calories for m in meals)
        remaining = settings.DAILY_CALORIE_BUDGET - total_cals
        status_word = f"🟢 {remaining} kcal remaining" if remaining >= 0 else f"🔴 {abs(remaining)} kcal over budget"

        lines = [
            f"📊 *Today's Status ({today.strftime('%d %b')}):*\n",
            f"🎯 Budget: *{settings.DAILY_CALORIE_BUDGET} kcal*",
            f"🔥 Consumed: *{total_cals} kcal*",
            f"⚖️ Status: *{status_word}*\n",
            "*Logged Meals:*"
        ]
        for m in meals:
            time_str = m.created_at.strftime("%I:%M %p") if m.created_at else ""
            lines.append(f"• *{m.meal_type.capitalize()}* ({time_str}): {m.total_calories} kcal — _{m.raw_text[:50]}_")

        lines.append(f"\nSend *EOD* whenever you are done for the day!")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    finally:
        db.close()

async def undo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = date.today()
    db = SessionLocal()
    try:
        last_meal = db.query(MealLog).filter(MealLog.date == today).order_by(MealLog.id.desc()).first()
        if not last_meal:
            await update.message.reply_text("ℹ️ No meals found for today to undo.")
            return

        cals = last_meal.total_calories
        raw = last_meal.raw_text
        meal_type = last_meal.meal_type
        db.delete(last_meal)
        db.commit()

        await update.message.reply_text(
            f"🗑️ *Deleted last entry:*\n"
            f"• *{meal_type.capitalize()}*: {cals} kcal\n"
            f"• '_{raw}_'\n\n"
            f"Your daily total has been recalculated.",
            parse_mode=ParseMode.MARKDOWN
        )
    finally:
        db.close()

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # In local testing it's localhost:8000, in production it would be domain
    msg = (
        f"🌐 *CalorieBot Web Dashboard:*\n"
        f"Open in your browser: `http://localhost:{settings.PORT}/dashboard`\n\n"
        f"View real-time charts, daily progress, macro splits, and download historical reports!"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def handle_eod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = date.today()
    await update.message.reply_text("⏳ *Analyzing today's intake and generating your daily audit & PDF report...*", parse_mode=ParseMode.MARKDOWN)
    
    db = SessionLocal()
    try:
        meals = db.query(MealLog).filter(MealLog.date == today).all()
        if not meals:
            await update.message.reply_text("ℹ️ No meals were logged today yet. Log at least one meal before generating your EOD report!")
            return

        analysis = analyze_day_meals(meals, budget=settings.DAILY_CALORIE_BUDGET)
        text_report = format_telegram_eod_report(today, analysis)
        pdf_path = generate_pdf_report(today, analysis)

        # Save to DailyReport table
        existing = db.query(DailyReport).filter(DailyReport.date == today).first()
        if not existing:
            existing = DailyReport(date=today)
            db.add(existing)
        existing.total_calories = analysis["total_calories"]
        existing.budget = analysis["budget"]
        existing.excess_calories = analysis["excess_calories"]
        existing.analysis_text = "\n".join(analysis["control_points"])
        existing.pdf_path = pdf_path
        db.commit()

        # Send text report
        await update.message.reply_text(text_report, parse_mode=ParseMode.MARKDOWN)

        # Send PDF report document
        with open(pdf_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=f"CalorieBot_Report_{today.strftime('%Y_%m_%d')}.pdf",
                caption=f"📄 Nutrition Audit Report — {today.strftime('%d %b %Y')}"
            )
    except Exception as e:
        logger.error(f"Error handling EOD: {e}", exc_info=True)
        await update.message.reply_text(f"⚠️ An error occurred generating report: {e}")
    finally:
        db.close()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    
    # Check if user sent EOD
    if text.upper() in ["EOD", "/EOD", "END OF DAY", "DONE FOR TODAY"]:
        await handle_eod(update, context)
        return

    # Check if user asked status
    if text.lower() in ["status", "/status", "today"]:
        await status_command(update, context)
        return

    # User logged food! Send quick typing action
    await update.effective_chat.send_action("typing")

    try:
        today = date.today()
        ref_meal_type = detect_meal_reference(text)
        
        if ref_meal_type:
            db = SessionLocal()
            try:
                prev_meal = (
                    db.query(MealLog)
                    .filter(MealLog.date == today, MealLog.meal_type == ref_meal_type)
                    .order_by(MealLog.id.desc())
                    .first()
                )
                if not prev_meal:
                    await update.message.reply_text(
                        f"⚠️ I couldn't find a logged *{ref_meal_type.capitalize()}* today to copy from!\n"
                        f"Please tell me what you ate for {extract_meal_type_heuristic(text)}.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return

                target_meal_type = extract_meal_type_heuristic(text)
                if target_meal_type == "other":
                    target_meal_type = "dinner" if ref_meal_type == "lunch" else "lunch"

                items = json.loads(prev_meal.items_json) if prev_meal.items_json else []
                total_cals = prev_meal.total_calories
                total_p = prev_meal.total_protein
                total_c = prev_meal.total_carbs
                total_f = prev_meal.total_fat
                tip = f"Copied accurately from your {ref_meal_type.capitalize()}."
                meal_type = target_meal_type
            finally:
                db.close()
        else:
            parsed = parse_food_with_gemini(text)
            meal_type = parsed.get("meal_type", "other")
            items = parsed.get("items", [])
            total_cals = parsed.get("total_calories", 0)
            total_p = parsed.get("total_protein", 0.0)
            total_c = parsed.get("total_carbs", 0.0)
            total_f = parsed.get("total_fat", 0.0)
            tip = parsed.get("short_tip", "")

        db = SessionLocal()
        try:
            meal_log = MealLog(
                date=today,
                meal_type=meal_type,
                raw_text=text,
                items_json=json.dumps(items),
                total_calories=total_cals,
                total_protein=total_p,
                total_carbs=total_c,
                total_fat=total_f,
            )
            db.add(meal_log)
            db.commit()
            db.refresh(meal_log)

            # Compute running day totals
            today_meals = db.query(MealLog).filter(MealLog.date == today).all()
            running_cals = sum(m.total_calories for m in today_meals)
            remaining_cals = settings.DAILY_CALORIE_BUDGET - running_cals
        finally:
            db.close()

        # Format quick response
        meal_icons = {
            "breakfast": "🌅",
            "lunch": "☀️",
            "snack": "☕",
            "dinner": "🌙",
            "meanwhile": "🕒",
            "other": "🍽️"
        }
        icon = meal_icons.get(meal_type, "🍽️")

        lines = [
            f"✅ *{icon} {meal_type.capitalize()} Logged!*",
        ]
        
        for item in items:
            name = item.get("name", "Item")
            qty = item.get("quantity", "1")
            unit = item.get("unit", "")
            cal = item.get("calories", 0)
            lines.append(f"• *{name}* ({qty} {unit}) — `{cal} kcal`".replace(" ()", ""))

        status_tag = f"🟢 `{remaining_cals} kcal` remaining" if remaining_cals >= 0 else f"🔴 `+{abs(remaining_cals)} kcal` OVER"

        lines.append(f"\n⚡ *Meal Total:* `{total_cals} kcal` (P: {total_p}g | C: {total_c}g | F: {total_f}g)")
        lines.append(f"📈 *Today So Far:* `{running_cals}` / *{settings.DAILY_CALORIE_BUDGET} kcal*")
        lines.append(f"⚖️ *Status:* {status_tag}")
        
        if tip:
            lines.append(f"\n💡 _{tip}_")

        lines.append("\n_Type 'EOD' when finished all meals for your full report!_")

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        await update.message.reply_text(f"⚠️ Error logging meal: {e}")

def create_bot_app() -> Application:
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN is not set. Telegram bot will not start.")
        return None

    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("undo", undo_command))
    app.add_handler(CommandHandler("dashboard", dashboard_command))
    app.add_handler(CommandHandler("eod", handle_eod))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    return app
