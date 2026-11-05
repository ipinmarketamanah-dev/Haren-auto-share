
import os
import json
from datetime import time
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)

TOKEN = os.getenv("8889726963:AAGrCQTuisMP5sLZ9Olax-vCV8ILbhVEDzc")
ADMIN_ID = int(os.getenv("ADMIN_ID", "
8833167773"))
FILE = "data.json"
TZ = ZoneInfo("Asia/Jakarta")

data = {
    "groups": [],
    "message": "Halo! Ini pesan promosi kami.",
    "hour": 9,
    "minute": 0,
    "active": False
}

def load_data():
    global data
    try:
        with open(FILE, "r") as f:
            data.update(json.load(f))
    except FileNotFoundError:
        pass

def save_data():
    with open(FILE, "w") as f:
        json.dump(data, f)

def is_admin(update):
    return update.effective_user.id == ADMIN_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 HAREN AUTO SHARE\n\n"
        "/settext - Atur pesan\n"
        "/settime - Atur jam\n"
        "/startshare - Mulai jadwal\n"
        "/stopshare - Hentikan jadwal\n"
        "/status - Cek status\n\n"
        "Untuk mendaftarkan grup, admin grup gunakan /register."
    )

async def register(update: Update, context):
    chat = update.effective_chat
    member = await chat.get_member(update.effective_user.id)

    if member.status not in ("administrator", "creator"):
        await update.message.reply_text(
            "Hanya admin grup yang boleh mendaftarkan grup."
        )
        return

    if chat.id not in data["groups"]:
        data["groups"].append(chat.id)
        save_data()

    await update.message.reply_text(
        "Grup berhasil didaftarkan untuk pesan terjadwal."
    )

async def unregister(update: Update, context):
    chat = update.effective_chat
    member = await chat.get_member(update.effective_user.id)

    if member.status not in ("administrator", "creator"):
        return

    if chat.id in data["groups"]:
        data["groups"].remove(chat.id)
        save_data()

    await update.message.reply_text("Grup berhasil dikeluarkan.")

async def settext(update: Update, context):
    if not is_admin(update):
        return

    text = update.message.text.partition(" ")[2].strip()
    if not text:
        await update.message.reply_text(
            "Gunakan: /settext isi pesan promosi"
        )
        return

    data["message"] = text
    save_data()
    await update.message.reply_text("Pesan berhasil disimpan.")

async def settime(update: Update, context):
    if not is_admin(update):
        return

    try:
        h, m = map(int, context.args[0].split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError

        data["hour"] = h
        data["minute"] = m
        save_data()

        await update.message.reply_text(
            f"Jam share diatur ke {h:02d}:{m:02d} WIB."
        )

        if data["active"]:
            schedule(context.application)

    except (ValueError, IndexError):
        await update.message.reply_text(
            "Format salah. Contoh: /settime 09:00"
        )

async def send_scheduled(context):
    for group_id in list(data["groups"]):
        try:
            await context.bot.send_message(
                chat_id=group_id,
                text=data["message"]
            )
        except Exception:
            # Grup yang menolak pesan tidak akan dicoba terus-menerus.
            continue

def schedule(app):
    jobs = app.job_queue.get_jobs_by_name("daily_share")
    for job in jobs:
        job.schedule_removal()

    app.job_queue.run_daily(
        send_scheduled,
        time=time(
            data["hour"],
            data["minute"],
            tzinfo=TZ
        ),
        name="daily_share"
    )

async def startshare(update: Update, context):
    if not is_admin(update):
        return

    if not data["groups"]:
        await update.message.reply_text(
            "Belum ada grup yang menyetujui pendaftaran."
        )
        return

    data["active"] = True
    save_data()
    schedule(context.application)
    await update.message.reply_text("AUTO SHARE AKTIF.")

async def stopshare(update: Update, context):
    if not is_admin(update):
        return

    data["active"] = False
    save_data()

    for job in context.application.job_queue.get_jobs_by_name(
        "daily_share"
    ):
        job.schedule_removal()

    await update.message.reply_text("AUTO SHARE DIHENTIKAN.")

async def status(update: Update, context):
    if not is_admin(update):
        return

    state = "AKTIF" if data["active"] else "NONAKTIF"
    await update.message.reply_text(
        f"STATUS: {state}\n"
        f"Jumlah grup: {len(data['groups'])}\n"
        f"Jadwal: {data['hour']:02d}:{data['minute']:02d} WIB"
    )

def main():
    if not TOKEN or not ADMIN_ID:
        raise RuntimeError("BOT_TOKEN dan ADMIN_ID wajib diatur.")

    load_data()

    app = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("unregister", unregister))
    app.add_handler(CommandHandler("settext", settext))
    app.add_handler(CommandHandler("settime", settime))
    app.add_handler(CommandHandler("startshare", startshare))
    app.add_handler(CommandHandler("stopshare", stopshare))
    app.add_handler(CommandHandler("status", status))

    if data["active"]:
        schedule(app)

    print("HAREN AUTO SHARE berjalan.")
    app.run_polling()

if __name__ == "__main__":
    main()
