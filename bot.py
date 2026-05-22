"""
Öğrenci Asistanı Telegram Botu
================================
Üniversite öğrencileri için devamsızlık, not, akademik takvim
ve materyal arşivi takibi yapan asenkron Telegram botu.

Gereksinimler:
    pip install python-telegram-bot>=20.0

Çalıştırma:
    BOT_TOKEN ortam değişkenini ayarlayın, ardından:
    python bot.py
"""

import os
import logging
import sqlite3
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# ──────────────────────────────────────────────
# Logging Yapılandırması
# ──────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Sabitler
# ──────────────────────────────────────────────
DB_NAME = "ogrenci_bot.db"
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ──────────────────────────────────────────────
# Veritabanı Kurulumu
# ──────────────────────────────────────────────

def setup_database() -> None:
    """
    Uygulama başlatıldığında çağrılır.
    Tablolar yoksa oluşturur; örnek takvim verilerini ekler.
    """
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # 1) attendance — Devamsızlık Tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                course_name TEXT    NOT NULL,
                absent_count INTEGER DEFAULT 0,
                max_limit   INTEGER DEFAULT 4,
                UNIQUE(user_id, course_name)
            )
        """)

        # 2) grades — Not Tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grades (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                course_name TEXT    NOT NULL,
                midterm     REAL,
                final       REAL,
                UNIQUE(user_id, course_name)
            )
        """)

        # 3) materials — Materyal Arşivi
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                course_name TEXT    NOT NULL,
                link_or_text TEXT   NOT NULL
            )
        """)

        # 4) calendar — Akademik Takvim
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calendar (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                semester   TEXT NOT NULL,
                emoji      TEXT NOT NULL DEFAULT '📌',
                event_name TEXT NOT NULL,
                event_date TEXT NOT NULL,
                UNIQUE(event_name, event_date)
            )
        """)

        # Kapsamlı akademik takvim verileri (KOÜ 2025-2026)
        sample_events = [
            # ── 🍁 GÜZ YARIYILI ──
            ("GÜZ YARIYILI (2025-2026)", "🍁", "Güz Dönemi Katkı Payı ve Harç Ücreti Ödemeleri Başlangıcı", "2025-09-08"),
            ("GÜZ YARIYILI (2025-2026)", "🎓", "Güz Dönemi Kayıt Yenileme ve Derse Yazılma Başlangıcı", "2025-09-08"),
            ("GÜZ YARIYILI (2025-2026)", "🎓", "Güz Dönemi Kayıt Yenileme ve Derse Yazılma Sonu", "2025-09-10"),
            ("GÜZ YARIYILI (2025-2026)", "📝", "Güz Dönemi Ders Ekleme/Bırakma ve Danışman Onayları Başlangıcı", "2025-09-11"),
            ("GÜZ YARIYILI (2025-2026)", "🏫", "Güz Dönemi Derslerin Başlangıcı", "2025-09-15"),
            ("GÜZ YARIYILI (2025-2026)", "🎓", "Güz Dönemi Ders Ekleme/Bırakma ve Danışman Onayları Sonu", "2025-09-19"),
            ("GÜZ YARIYILI (2025-2026)", "🇹🇷", "Cumhuriyet Bayramı (Resmi Tatil - 1.5 Gün)", "2025-10-29"),
            ("GÜZ YARIYILI (2025-2026)", "🎗️", "Atatürk'ü Anma Günü Törenleri", "2025-11-10"),
            ("GÜZ YARIYILI (2025-2026)", "📝", "Güz Dönemi Ara Sınavları (Vizeler) Başlangıcı", "2025-11-17"),
            ("GÜZ YARIYILI (2025-2026)", "📝", "Güz Dönemi Ara Sınavları (Vizeler) Sonu", "2025-11-21"),
            ("GÜZ YARIYILI (2025-2026)", "📝", "Güz Dönemi Mazeret Sınavları Başlangıcı", "2025-12-22"),
            ("GÜZ YARIYILI (2025-2026)", "📝", "Güz Dönemi Mazeret Sınavları Sonu", "2025-12-26"),
            ("GÜZ YARIYILI (2025-2026)", "🎉", "Yılbaşı Tatili (Resmi Tatil - 1 Gün)", "2026-01-01"),
            ("GÜZ YARIYILI (2025-2026)", "🏫", "Güz Dönemi Derslerinin Sonu", "2026-01-02"),
            ("GÜZ YARIYILI (2025-2026)", "📝", "Güz Dönemi Yarıyıl Sonu Sınavları (Finaller) Başlangıcı", "2026-01-05"),
            ("GÜZ YARIYILI (2025-2026)", "📝", "Güz Dönemi Yarıyıl Sonu Sınavları (Finaller) Sonu", "2026-01-16"),
            ("GÜZ YARIYILI (2025-2026)", "💾", "Güz Dönemi Not Girişlerinin Son Günü (ÖBS Sürümü)", "2026-01-20"),
            ("GÜZ YARIYILI (2025-2026)", "📝", "Güz Dönemi Bütünleme Sınavları Başlangıcı", "2026-01-26"),
            ("GÜZ YARIYILI (2025-2026)", "💼", "Bahar Dönemi Yatay Geçiş Başvurularının Başlaması", "2026-01-26"),
            ("GÜZ YARIYILI (2025-2026)", "📝", "Güz Dönemi Bütünleme Sınavları Sonu", "2026-01-30"),
            ("GÜZ YARIYILI (2025-2026)", "🎓", "Güz Dönemi Tek Ders Sınavı", "2026-02-05"),
            # ── 🌸 BAHAR YARIYILI ──
            ("BAHAR YARIYILI (2025-2026)", "🌸", "Bahar Dönemi Kayıt Yenileme, Harç Yatırma ve Derse Yazılma Başlangıcı", "2026-02-09"),
            ("BAHAR YARIYILI (2025-2026)", "🎓", "Bahar Dönemi Kayıt Yenileme ve Derse Yazılma Sonu", "2026-02-11"),
            ("BAHAR YARIYILI (2025-2026)", "🏫", "Bahar Dönemi Derslerin Başlangıcı", "2026-02-16"),
            ("BAHAR YARIYILI (2025-2026)", "🌙", "Ramazan Bayramı Tatili (Resmi Tatil - 3.5 Gün)", "2026-03-20"),
            ("BAHAR YARIYILI (2025-2026)", "📝", "Bahar Dönemi Ara Sınavları (Vizeler) Başlangıcı", "2026-04-13"),
            ("BAHAR YARIYILI (2025-2026)", "📝", "Bahar Dönemi Ara Sınavları (Vizeler) Sonu", "2026-04-17"),
            ("BAHAR YARIYILI (2025-2026)", "🇹🇷", "Ulusal Egemenlik ve Çocuk Bayramı (Resmi Tatil)", "2026-04-23"),
            ("BAHAR YARIYILI (2025-2026)", "👷", "Emek ve Dayanışma Günü (Resmi Tatil)", "2026-05-01"),
            ("BAHAR YARIYILI (2025-2026)", "🇹🇷", "Atatürk'ü Anma, Gençlik ve Spor Bayramı (Resmi Tatil)", "2026-05-19"),
            ("BAHAR YARIYILI (2025-2026)", "🐏", "Kurban Bayramı Tatili (Resmi Tatil - 4.5 Gün)", "2026-05-27"),
            ("BAHAR YARIYILI (2025-2026)", "🏫", "Bahar Dönemi Derslerinin Sonu", "2026-06-12"),
            ("BAHAR YARIYILI (2025-2026)", "📝", "Bahar Dönemi Yarıyıl Sonu Sınavları (Finaller) Başlangıcı", "2026-06-15"),
            ("BAHAR YARIYILI (2025-2026)", "📝", "Bahar Dönemi Yarıyıl Sonu Sınavları (Finaller) Sonu", "2026-06-24"),
            ("BAHAR YARIYILI (2025-2026)", "📝", "Bahar Dönemi Bütünleme Sınavları Başlangıcı", "2026-07-02"),
            ("BAHAR YARIYILI (2025-2026)", "📝", "Bahar Dönemi Bütünleme Sınavları Sonu", "2026-07-08"),
            ("BAHAR YARIYILI (2025-2026)", "🇹🇷", "Demokrasi ve Milli Birlik Günü (Resmi Tatil)", "2026-07-15"),
            ("BAHAR YARIYILI (2025-2026)", "🎓", "Bahar Dönemi Tek Ders Sınavı", "2026-07-15"),
            # ── ☀️ YAZ OKULU DÖNEMİ ──
            ("YAZ OKULU DÖNEMİ (2026)", "☀️", "Yaz Okulu Başvuruları ve Derse Yazılma Kayıtları Başlangıcı", "2026-07-20"),
            ("YAZ OKULU DÖNEMİ (2026)", "🏫", "Yaz Okulu Derslerinin Başlangıcı", "2026-07-27"),
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO calendar (semester, emoji, event_name, event_date) VALUES (?, ?, ?, ?)",
            sample_events,
        )
        conn.commit()

    logger.info("Veritabanı başarıyla kuruldu / doğrulandı.")


# ──────────────────────────────────────────────
# Komut İşleyicileri (Handlers)
# ──────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /start — Kullanıcıyı selamlar ve tüm komutları listeler.
    """
    welcome_text = (
        "👋 *Merhaba! Öğrenci Asistanı Bot'a hoş geldin!*\n\n"
        "Kullanabileceğin komutlar:\n\n"
        "📅 /takvim — Akademik takvimi görüntüle\n\n"
        "📝 *Devamsızlık:*\n"
        "  • /devamsizlik\\_ekle `[Ders Adı]` — Devamsızlık ekle\n"
        "  • /devamsizlik\\_durum — Devamsızlık durumunu gör\n\n"
        "🎓 *Notlar:*\n"
        "  • /not\\_ekle `[Ders Adı] [Vize] [Final]` — Not ekle/güncelle\n"
        "  • /not\\_durum — Not durumunu ve ortalamaları gör\n\n"
        "📚 *Materyal Arşivi:*\n"
        "  • /arsiv\\_ekle `[Ders Adı] [Link/İçerik]` — Materyal kaydet\n"
        "  • /arsiv\\_getir — Kayıtlı materyalleri listele\n"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")
    logger.info("Kullanıcı %s /start komutunu kullandı.", update.effective_user.id)


# Türkçe gün adları için yardımcı sözlük
GUN_ADLARI = {
    "Monday": "Pazartesi",
    "Tuesday": "Salı",
    "Wednesday": "Çarşamba",
    "Thursday": "Perşembe",
    "Friday": "Cuma",
    "Saturday": "Cumartesi",
    "Sunday": "Pazar",
}

# Türkçe ay adları
AY_ADLARI = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan",
    5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos",
    9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık",
}


def format_tarih(date_str: str) -> str:
    """'2026-01-05' → '5 Ocak 2026, Pazartesi' formatına çevirir."""
    from datetime import datetime
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    gun_adi = GUN_ADLARI.get(dt.strftime("%A"), "")
    ay_adi = AY_ADLARI.get(dt.month, "")
    return f"{dt.day} {ay_adi} {dt.year}, {gun_adi}"


async def takvim(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /takvim — Akademik takvimi dönem bazlı gruplandırarak listeler.
    """
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT semester, emoji, event_name, event_date FROM calendar ORDER BY event_date ASC"
        )
        rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("📅 Takvimde herhangi bir etkinlik bulunamadı.")
        return

    # Dönem bazlı grupla
    semesters: dict[str, list] = {}
    for semester, emoji, event_name, event_date in rows:
        if semester not in semesters:
            semesters[semester] = []
        semesters[semester].append((emoji, event_name, event_date))

    # Her dönem için ayrı mesaj gönder (Telegram mesaj uzunluk limiti)
    for semester_name, events in semesters.items():
        # Dönem başlığı emoji
        if "GÜZ" in semester_name:
            header_emoji = "🍁"
        elif "YAZ" in semester_name:
            header_emoji = "☀️"
        else:
            header_emoji = "🌸"
        lines = [f"{header_emoji} {semester_name}\n"]

        for emoji, event_name, event_date in events:
            tarih = format_tarih(event_date)
            lines.append(f"• {tarih}")
            lines.append(f"  L {emoji} {event_name}\n")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def devamsizlik_ekle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /devamsizlik_ekle [Ders Adı]
    Verilen ders yoksa 1 devamsızlıkla oluşturur. Varsa sayacı 1 artırır.
    Sınır aşıldıysa uyarı verir.
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ Kullanım: /devamsizlik_ekle [Ders Adı]\n"
            "Örnek: /devamsizlik_ekle Matematik"
        )
        return

    user_id = update.effective_user.id
    course_name = " ".join(context.args)

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Mevcut kaydı kontrol et
        cursor.execute(
            "SELECT absent_count, max_limit FROM attendance WHERE user_id = ? AND course_name = ?",
            (user_id, course_name),
        )
        row = cursor.fetchone()

        if row is None:
            # Yeni ders kaydı oluştur (1 devamsızlıkla)
            cursor.execute(
                "INSERT INTO attendance (user_id, course_name, absent_count) VALUES (?, ?, 1)",
                (user_id, course_name),
            )
            conn.commit()
            await update.message.reply_text(
                f"✅ *{course_name}* dersi eklendi. Devamsızlık: 1/4",
                parse_mode="Markdown",
            )
        else:
            absent_count = row[0] + 1
            max_limit = row[1]

            cursor.execute(
                "UPDATE attendance SET absent_count = ? WHERE user_id = ? AND course_name = ?",
                (absent_count, user_id, course_name),
            )
            conn.commit()

            msg = f"✅ *{course_name}* — Devamsızlık: {absent_count}/{max_limit}"

            if absent_count >= max_limit:
                msg += "\n\n⚠️ *DİKKAT: Devamsızlık sınırına ulaştınız veya aştınız!*"

            await update.message.reply_text(msg, parse_mode="Markdown")

    logger.info(
        "Kullanıcı %s, '%s' dersine devamsızlık ekledi.", user_id, course_name
    )


async def devamsizlik_durum(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /devamsizlik_durum — Kullanıcının tüm devamsızlıklarını listeler.
    """
    user_id = update.effective_user.id

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT course_name, absent_count, max_limit FROM attendance WHERE user_id = ?",
            (user_id,),
        )
        rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("📋 Henüz kayıtlı devamsızlık bulunamadı.")
        return

    lines = ["📋 *Devamsızlık Durumun:*\n"]
    for course_name, absent_count, max_limit in rows:
        status = "⚠️" if absent_count >= max_limit else "✅"
        lines.append(f"  {status} *{course_name}:* {absent_count}/{max_limit}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def not_ekle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /not_ekle [Ders Adı] [Vize] [Final]
    Son iki argüman vize ve final notudur; geri kalanı ders adıdır.
    Upsert mantığıyla çalışır.
    """
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "⚠️ Kullanım: /not_ekle [Ders Adı] [Vize] [Final]\n"
            "Örnek: /not_ekle Algoritma Analizi 50 60"
        )
        return

    user_id = update.effective_user.id

    # Son iki eleman notlar, geri kalanı ders adı
    course_name = " ".join(context.args[:-2])
    raw_midterm = context.args[-2]
    raw_final = context.args[-1]

    # Ders adı boş kalmamalı
    if not course_name.strip():
        await update.message.reply_text(
            "⚠️ Ders adı belirtilmedi.\n"
            "Kullanım: /not_ekle [Ders Adı] [Vize] [Final]"
        )
        return

    # Sayısal doğrulama
    try:
        midterm = float(raw_midterm)
        final = float(raw_final)
    except ValueError:
        await update.message.reply_text(
            "⚠️ Vize ve Final değerleri sayı olmalıdır.\n"
            "Örnek: /not_ekle Matematik 70 85"
        )
        return

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # ON CONFLICT DO UPDATE — Upsert
        cursor.execute(
            """
            INSERT INTO grades (user_id, course_name, midterm, final)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, course_name)
            DO UPDATE SET midterm = excluded.midterm, final = excluded.final
            """,
            (user_id, course_name, midterm, final),
        )
        conn.commit()

    await update.message.reply_text(
        f"✅ *{course_name}* notları kaydedildi:\n"
        f"  • Vize: {midterm}\n"
        f"  • Final: {final}",
        parse_mode="Markdown",
    )
    logger.info(
        "Kullanıcı %s, '%s' dersine not ekledi (Vize: %s, Final: %s).",
        user_id, course_name, midterm, final,
    )


async def not_durum(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /not_durum — Kullanıcının tüm notlarını ve ortalamalarını listeler.
    Ortalama = (Vize × 0.4) + (Final × 0.6). >= 50 ise Geçti ✅, değilse Kaldı ❌.
    """
    user_id = update.effective_user.id

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT course_name, midterm, final FROM grades WHERE user_id = ?",
            (user_id,),
        )
        rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("📋 Henüz kayıtlı not bulunamadı.")
        return

    lines = ["🎓 *Not Durumun:*\n"]
    for course_name, midterm, final in rows:
        average = (midterm * 0.4) + (final * 0.6)
        status = "Geçti ✅" if average >= 50 else "Kaldı ❌"
        lines.append(
            f"  📘 *{course_name}*\n"
            f"      Vize: {midterm} | Final: {final} | "
            f"Ort: {average:.1f} — {status}"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def arsiv_ekle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /arsiv_ekle [Ders Adı] [Link/İçerik]
    İlk kelime ders adı, geri kalanı içerik/link olarak kaydedilir.
    Birden fazla kelimelik ders adları için ders adını tek kelime tutmak ya da
    tırnak kullanmak gereklidir — burada basitlik adına ilk kelime ders adıdır.
    """
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ Kullanım: /arsiv_ekle [Ders Adı] [Link veya İçerik]\n"
            "Örnek: /arsiv_ekle Matematik https://ornek.com/notlar.pdf"
        )
        return

    user_id = update.effective_user.id
    course_name = context.args[0]
    link_or_text = " ".join(context.args[1:])

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO materials (user_id, course_name, link_or_text) VALUES (?, ?, ?)",
            (user_id, course_name, link_or_text),
        )
        conn.commit()

    await update.message.reply_text(
        f"✅ *{course_name}* dersine materyal eklendi:\n  {link_or_text}",
        parse_mode="Markdown",
    )
    logger.info("Kullanıcı %s, '%s' dersine materyal ekledi.", user_id, course_name)


async def arsiv_getir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /arsiv_getir — Kullanıcının kayıtlı materyallerini listeler.
    """
    user_id = update.effective_user.id

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT course_name, link_or_text FROM materials WHERE user_id = ?",
            (user_id,),
        )
        rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("📚 Henüz kayıtlı materyal bulunamadı.")
        return

    lines = ["📚 *Materyal Arşivin:*\n"]
    for course_name, link_or_text in rows:
        lines.append(f"  📘 *{course_name}:* {link_or_text}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ──────────────────────────────────────────────
# Ana Giriş Noktası
# ──────────────────────────────────────────────

def main() -> None:
    """Botu başlatır."""
    # Token kontrolü
    if not BOT_TOKEN:
        logger.critical(
            "BOT_TOKEN ortam değişkeni bulunamadı! "
            "Lütfen 'BOT_TOKEN' ortam değişkenini ayarlayın."
        )
        raise SystemExit("BOT_TOKEN ortam değişkeni tanımlı değil.")

    # Veritabanını kur
    setup_database()

    # Application oluştur
    application = Application.builder().token(BOT_TOKEN).build()

    # Komut handler'larını kaydet
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("takvim", takvim))
    application.add_handler(CommandHandler("devamsizlik_ekle", devamsizlik_ekle))
    application.add_handler(CommandHandler("devamsizlik_durum", devamsizlik_durum))
    application.add_handler(CommandHandler("not_ekle", not_ekle))
    application.add_handler(CommandHandler("not_durum", not_durum))
    application.add_handler(CommandHandler("arsiv_ekle", arsiv_ekle))
    application.add_handler(CommandHandler("arsiv_getir", arsiv_getir))

    logger.info("Bot başlatılıyor...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
