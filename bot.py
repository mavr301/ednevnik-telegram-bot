import datetime
import logging
import os
from collections import defaultdict

import pytz
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from formatter import (
    format_all_by_subject,
    format_averages,
    format_new_grades,
    format_subject,
)
from scraper import EDnevnikScraper, Grade, LoginError
from storage import get_seen_uids, is_first_run, mark_seen

logger = logging.getLogger(__name__)


def _scraper() -> EDnevnikScraper:
    return EDnevnikScraper(
        username=os.environ["EDNEVNIK_USERNAME"],
        password=os.environ["EDNEVNIK_PASSWORD"],
    )


def _chat_id() -> Optional[str]:
    return os.environ.get("TELEGRAM_CHAT_ID")


# ── Commands ──────────────────────────────────────────────────────────────────


async def cmd_marks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show marks added since the last check."""
    await update.message.reply_text("Checking for new marks...")
    try:
        grades = _scraper().get_grades()
        seen = get_seen_uids()
        new = [g for g in grades if g.uid() not in seen]
        if new:
            mark_seen([g.uid() for g in new])
        await update.message.reply_text(format_new_grades(new))
    except LoginError as e:
        await update.message.reply_text(f"Login failed: {e}")
    except Exception as e:
        logger.exception("Error in /marks")
        await update.message.reply_text(f"Error: {e}")


async def cmd_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all marks grouped by subject (one message per subject)."""
    await update.message.reply_text("Fetching all marks...")
    try:
        grades = _scraper().get_grades()
        mark_seen([g.uid() for g in grades])
        messages = format_all_by_subject(grades)
        if not messages:
            await update.message.reply_text("No marks found.")
            return
        for msg in messages:
            await update.message.reply_text(f"```\n{msg}\n```", parse_mode="Markdown")
    except LoginError as e:
        await update.message.reply_text(f"Login failed: {e}")
    except Exception as e:
        logger.exception("Error in /all")
        await update.message.reply_text(f"Error: {e}")


async def cmd_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all marks for a subject. Partial name match, case-insensitive."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /subject <name>\nExample: /subject literacy"
        )
        return
    query = " ".join(context.args).lower()
    try:
        all_grades = _scraper().get_grades()
        by_subject: dict[str, list[Grade]] = defaultdict(list)
        teachers: dict[str, str] = {}
        for g in all_grades:
            if query in g.subject.lower():
                by_subject[g.subject].append(g)
                if g.teacher:
                    teachers[g.subject] = g.teacher

        if not by_subject:
            await update.message.reply_text(f'No subject matching "{query}" found.')
            return
        for subject, grades in sorted(by_subject.items()):
            msg = format_subject(subject, teachers.get(subject, ""), grades)
            await update.message.reply_text(f"```\n{msg}\n```", parse_mode="Markdown")
    except LoginError as e:
        await update.message.reply_text(f"Login failed: {e}")
    except Exception as e:
        logger.exception("Error in /subject")
        await update.message.reply_text(f"Error: {e}")


async def cmd_avg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show average grade per subject, sorted highest first."""
    try:
        grades = _scraper().get_grades()
        await update.message.reply_text(format_averages(grades))
    except LoginError as e:
        await update.message.reply_text(f"Login failed: {e}")
    except Exception as e:
        logger.exception("Error in /avg")
        await update.message.reply_text(f"Error: {e}")


async def cmd_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all subjects as clickable buttons."""
    try:
        all_grades = _scraper().get_grades()
        subjects = sorted({g.subject for g in all_grades})
        if not subjects:
            await update.message.reply_text("No subjects found.")
            return
        buttons = [
            InlineKeyboardButton(s, callback_data=f"sub:{s}")
            for s in subjects
        ]
        # Two buttons per row
        rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
        await update.message.reply_text(
            "📋 Choose a subject:",
            reply_markup=InlineKeyboardMarkup(rows),
        )
    except LoginError as e:
        await update.message.reply_text(f"Login failed: {e}")
    except Exception as e:
        logger.exception("Error in /subjects")
        await update.message.reply_text(f"Error: {e}")


async def on_subject_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle subject button taps."""
    query = update.callback_query
    allowed_raw = os.environ.get("ALLOWED_USER_IDS", "")
    if allowed_raw.strip():
        allowed = [int(x.strip()) for x in allowed_raw.split(",") if x.strip()]
        if query.from_user.id not in allowed:
            await query.answer("Not authorized.", show_alert=True)
            return
    await query.answer()

    subject = query.data.removeprefix("sub:")
    try:
        all_grades = _scraper().get_grades()
        grades = [g for g in all_grades if g.subject == subject]
        teacher = next((g.teacher for g in grades if g.teacher), "")
        msg = format_subject(subject, teacher, grades)
        await query.edit_message_text(f"```\n{msg}\n```", parse_mode="Markdown")
    except LoginError as e:
        await query.edit_message_text(f"Login failed: {e}")
    except Exception as e:
        logger.exception("Error in subject button handler")
        await query.edit_message_text(f"Error: {e}")


# ── Scheduled daily check ─────────────────────────────────────────────────────


async def daily_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = _chat_id()
    logger.info("Running daily grade check")
    try:
        scraper = _scraper()
        first_run = is_first_run()
        all_grades = scraper.get_grades()
        seen = get_seen_uids()
        new = [g for g in all_grades if g.uid() not in seen]

        if first_run:
            mark_seen([g.uid() for g in all_grades])
            messages = format_all_by_subject(all_grades)
            total = len(all_grades)
            await context.bot.send_message(
                chat_id,
                f"📋 Bot started — loaded {total} existing marks across {len(messages)} subjects.",
            )
            for msg in messages:
                await context.bot.send_message(
                    chat_id, f"```\n{msg}\n```", parse_mode="Markdown"
                )
        elif new:
            mark_seen([g.uid() for g in new])
            await context.bot.send_message(chat_id, format_new_grades(new))
        else:
            logger.info("No new grades")
    except LoginError as e:
        logger.error("Daily check login error: %s", e)
        await context.bot.send_message(chat_id, f"⚠️ Login failed: {e}")
    except Exception as e:
        logger.exception("Daily check error")
        await context.bot.send_message(chat_id, f"⚠️ Grade check failed: {e}")


# ── App builder ───────────────────────────────────────────────────────────────


def _allowed_filter():
    raw = os.environ.get("ALLOWED_USER_IDS", "")
    if not raw.strip():
        return None
    from telegram.ext import filters
    ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
    return filters.User(user_id=ids)


def build_app() -> Application:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    user_filter = _allowed_filter()
    if user_filter is None:
        logger.warning("ALLOWED_USER_IDS not set — bot responds to everyone")

    def handler(cmd, callback):
        if user_filter is not None:
            return CommandHandler(cmd, callback, filters=user_filter)
        return CommandHandler(cmd, callback)

    app.add_handler(handler("marks", cmd_marks))
    app.add_handler(handler("all", cmd_all))
    app.add_handler(handler("subject", cmd_subject))
    app.add_handler(handler("subjects", cmd_subjects))
    app.add_handler(handler("avg", cmd_avg))

    app.add_handler(CallbackQueryHandler(on_subject_button, pattern="^sub:"))

    check_time_str = os.getenv("DAILY_CHECK_TIME", "08:00")
    tz_name = os.getenv("TIMEZONE", "Europe/Zagreb")
    tz = pytz.timezone(tz_name)
    hour, minute = (int(x) for x in check_time_str.split(":"))
    check_time = datetime.time(hour=hour, minute=minute, tzinfo=tz)

    if _chat_id():
        app.job_queue.run_daily(daily_check, time=check_time, name="daily_grade_check")
        logger.info("Daily check scheduled at %s %s", check_time_str, tz_name)
    else:
        logger.warning("TELEGRAM_CHAT_ID not set — daily check disabled")

    return app
