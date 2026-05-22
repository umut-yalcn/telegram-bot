"""
Öğrenci Asistanı Telegram Botu
Gereksinimler: python-telegram-bot>=20.0, Python 3.10+
Kurulum  : pip install python-telegram-bot
Çalıştırma: BOT_TOKEN=<token> python bot.py
"""

import logging
import os
import sqlite3
import html
import time
import urllib.request
import json
import datetime

from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes

# ---------------------------------------------------------------------------
# Logging Yapılandırması
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sabitler ve Önbellek Tanımları
# ---------------------------------------------------------------------------
DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ogrenci_bot.db")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Canlı Duyuru Önbelleği (5 dakika - Sunucu yormama ve Spam Koruması)
ANNOUNCEMENT_CACHE = None
CACHE_TIMESTAMP = 0
CACHE_DURATION_SECS = 300

# ---------------------------------------------------------------------------
# Veritabanı Kurulumu
# ---------------------------------------------------------------------------

def setup_database() -> None:
    """Gerekli tabloları oluşturur ve örnek takvim verilerini ekler."""
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()

        # 1) Devamsızlık tablosu
        cur.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                course_name  TEXT    NOT NULL,
                absent_count INTEGER NOT NULL DEFAULT 0,
                max_limit    INTEGER NOT NULL DEFAULT 4,
                UNIQUE(user_id, course_name)
            )
        """)

        # 2) Notlar tablosu
        cur.execute("""
            CREATE TABLE IF NOT EXISTS grades (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                course_name TEXT    NOT NULL,
                midterm     REAL,
                final       REAL,
                UNIQUE(user_id, course_name)
            )
        """)

        # 3) Materyal arşivi tablosu
        cur.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                course_name  TEXT    NOT NULL,
                link_or_text TEXT    NOT NULL
            )
        """)

        # 4) Akademik takvim tablosu
        cur.execute("""
            CREATE TABLE IF NOT EXISTS calendar (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT NOT NULL,
                event_date TEXT NOT NULL,
                UNIQUE(event_name, event_date)
            )
        """)

        # Önceki takvim verilerini sıfırla (temiz ver kurulumu)
        cur.execute("DELETE FROM calendar")

        # Resmi Kocaeli Üniversitesi 2025-2026 Akademik Takvimi verileri
        sample_events = [
            ("🍁 Güz Dönemi Katkı Payı ve Harç Ücreti Ödemeleri Başlangıcı", "2025-09-08"),
            ("🎓 Güz Dönemi Kayıt Yenileme ve Derse Yazılma Başlangıcı", "2025-09-08"),
            ("🎓 Güz Dönemi Kayıt Yenileme ve Derse Yazılma Sonu", "2025-09-10"),
            ("📝 Güz Dönemi Ders Ekleme/Bırakma ve Danışman Onayları Başlangıcı", "2025-09-11"),
            ("🏫 Güz Dönemi Derslerin Başlangıcı", "2025-09-15"),
            ("🎓 Güz Dönemi Ders Ekleme/Bırakma ve Danışman Onayları Sonu", "2025-09-19"),
            ("🇹🇷 Cumhuriyet Bayramı (Resmi Tatil - 1.5 Gün)", "2025-10-29"),
            ("🎗️ Atatürk'ü Anma Günü Törenleri", "2025-11-10"),
            ("📝 Güz Dönemi Ara Sınavları (Vizeler) Başlangıcı", "2025-11-17"),
            ("📝 Güz Dönemi Ara Sınavları (Vizeler) Sonu", "2025-11-21"),
            ("📝 Güz Dönemi Mazeret Sınavları Başlangıcı", "2025-12-22"),
            ("📝 Güz Dönemi Mazeret Sınavları Sonu", "2025-12-26"),
            ("🎉 Yılbaşı Tatili (Resmi Tatil - 1 Gün)", "2026-01-01"),
            ("🏫 Güz Dönemi Derslerinin Sonu", "2026-01-02"),
            ("📝 Güz Dönemi Yarıyıl Sonu Sınavları (Finaller) Başlangıcı", "2026-01-05"),
            ("📝 Güz Dönemi Yarıyıl Sonu Sınavları (Finaller) Sonu", "2026-01-16"),
            ("💾 Güz Dönemi Not Girişlerinin Son Günü (ÖBS Sürümü)", "2026-01-20"),
            ("📝 Güz Dönemi Bütünleme Sınavları Başlangıcı", "2026-01-26"),
            ("📝 Güz Dönemi Bütünleme Sınavları Sonu", "2026-01-30"),
            ("💼 Bahar Dönemi Yatay Geçiş Başvurularının Başlaması", "2026-01-26"),
            ("🎓 Güz Dönemi Tek Ders Sınavı", "2026-02-05"),
            ("🌸 Bahar Dönemi Kayıt Yenileme, Harç Yatırma ve Derse Yazılma Başlangıcı", "2026-02-09"),
            ("🎓 Bahar Dönemi Kayıt Yenileme ve Derse Yazılma Sonu", "2026-02-11"),
            ("🏫 Bahar Dönemi Derslerin Başlangıcı", "2026-02-16"),
            ("🌙 Ramazan Bayramı Tatili (Resmi Tatil - 3.5 Gün)", "2026-03-20"),
            ("📝 Bahar Dönemi Ara Sınavları (Vizeler) Başlangıcı", "2026-04-13"),
            ("📝 Bahar Dönemi Ara Sınavları (Vizeler) Sonu", "2026-04-17"),
            ("🇹🇷 Ulusal Egemenlik ve Çocuk Bayramı (Resmi Tatil)", "2026-04-23"),
            ("👷 Emek ve Dayanışma Günü (Resmi Tatil)", "2026-05-01"),
            ("🇹🇷 Atatürk'ü Anma, Gençlik ve Spor Bayramı (Resmi Tatil)", "2026-05-19"),
            ("🐏 Kurban Bayramı Tatili (Resmi Tatil - 4.5 Gün)", "2026-05-27"),
            ("🏫 Bahar Dönemi Derslerinin Sonu", "2026-06-12"),
            ("📝 Bahar Dönemi Yarıyıl Sonu Sınavları (Finaller) Başlangıcı", "2026-06-15"),
            ("📝 Bahar Dönemi Yarıyıl Sonu Sınavları (Finaller) Sonu", "2026-06-24"),
            ("📝 Bahar Dönemi Bütünleme Sınavları Başlangıcı", "2026-07-02"),
            ("📝 Bahar Dönemi Bütünleme Sınavları Sonu", "2026-07-08"),
            ("🇹🇷 Demokrasi ve Milli Birlik Günü (Resmi Tatil)", "2026-07-15"),
            ("🎓 Bahar Dönemi Tek Ders Sınavı", "2026-07-15"),
            ("☀️ Yaz Okulu Başvuruları ve Derse Yazılma Kayıtları Başlangıcı", "2026-07-20"),
            ("🏫 Yaz Okulu Derslerinin Başlangıcı", "2026-07-27"),
        ]
        
        cur.executemany(
            "INSERT OR IGNORE INTO calendar (event_name, event_date) VALUES (?, ?)",
            sample_events,
        )

        conn.commit()
    logger.info("Veritabanı kurulumu tamamlandı: %s", DB_NAME)


# ---------------------------------------------------------------------------
# Yardımcı Tarih ve Canlı API Fonksiyonları
# ---------------------------------------------------------------------------

def format_date_tr(date_str: str) -> str:
    """YYYY-MM-DD formatındaki tarihi 'D Ay YYYY, Gün' formatına çevirir."""
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        months = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        weekdays = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        return f"{dt.day} {months[dt.month]} {dt.year}, {weekdays[dt.weekday()]}"
    except Exception:
        return date_str


def fetch_live_announcements() -> list | None:
    """Kocaeli Üniversitesi BSM resmi API'sinden güncel son 20 duyuruyu çeker (5 dakika önbellekli)."""
    global ANNOUNCEMENT_CACHE, CACHE_TIMESTAMP
    
    now = time.time()
    if ANNOUNCEMENT_CACHE is not None and (now - CACHE_TIMESTAMP) < CACHE_DURATION_SECS:
        logger.info("Duyurular önbellekten (cache) servis ediliyor.")
        return ANNOUNCEMENT_CACHE

    url = "https://api.kocaeli.edu.tr/api/Announcement/GetAll"
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'code': '1061'  # Kocaeli Üniversitesi BSM Bölüm Kodu
        }
    )
    
    try:
        logger.info("Canlı duyurular KOÜ API sunucusundan talep ediliyor...")
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        all_items = []
        if data.get('success') and isinstance(data.get('data'), list):
            for item in data['data']:
                ann = item.get('announcement')
                if not ann or not ann.get('title') or not ann.get('startDate'):
                    continue
                
                title = ann['title'].strip()
                
                # Tarih ayrıştırma: "2026-05-18T10:00:00" -> "18.05.2026"
                try:
                    date_part = ann['startDate'].split('T')[0]
                    parts = date_part.split('-')
                    formatted_date = f"{parts[2]}.{parts[1]}.{parts[0]}"
                except Exception:
                    formatted_date = "-"

                seo_url = item.get('seoUrl', '').strip()
                # Güvenli URL doğrulama
                if seo_url and '/' not in seo_url and '\\' not in seo_url:
                    link = f"https://bilisim.kocaeli.edu.tr/tr/duyurular/{seo_url}"
                else:
                    link = "https://bilisim.kocaeli.edu.tr/tr/duyurular"

                all_items.append({
                    'title': title,
                    'date': formatted_date,
                    'link': link
                })
            
            # Tarih sıralaması API tarafından doğru döner, son 20 duyuruyu önbelleğe alıp döneriz
            ANNOUNCEMENT_CACHE = all_items[:20]
            CACHE_TIMESTAMP = now
            return ANNOUNCEMENT_CACHE
        else:
            logger.warning("Resmi API geçersiz veya başarısız veri döndürdü.")
            return None
    except Exception as e:
        logger.error("Canlı duyuru sorgusunda beklenmedik hata: %s", e)
        return None


# ---------------------------------------------------------------------------
# Komut İşleyicileri
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start — Kullanıcıyı karşılar ve komutları listeler."""
    kullanici = html.escape(update.effective_user.first_name or "Öğrenci")
    mesaj = (
        f"👋 Merhaba, <b>{kullanici}</b>! Ben Öğrenci Asistanı Botuyum.\n\n"
        "Kullanabileceğin komutlar:\n\n"
        "📅 <b>Akademik Takvim</b>\n"
        "  /takvim — Akademik etkinlikleri listeler.\n\n"
        "📢 <b>Canlı Duyurular</b>\n"
        "  /duyurular — Son 20 canlı BSM duyurusunu listeler.\n\n"
        "📋 <b>Devamsızlık</b>\n"
        "  /devamsizlik_ekle [Ders Adı] — Devamsızlık ekler.\n"
        "  /devamsizlik_sil [Ders Adı] — Devamsızlık sayısını 1 azaltır.\n"
        "  /devamsizlik_durum — Devamsızlık durumunu gösterir.\n\n"
        "📝 <b>Notlar</b>\n"
        "  /not_ekle [Ders Adı] [Vize] [Final] — Not ekler/günceller.\n"
        "  /not_durum — Notları ve geçme durumunu gösterir.\n\n"
        "📁 <b>Materyal Arşivi</b>\n"
        "  /arsiv_ekle [Ders Adı] [Link/İçerik] — Materyal kaydeder.\n"
        "  /arsiv_getir — Kayıtlı materyalleri listeler.\n\n"
        "🗑️ <b>Veri Yönetimi (KVKK)</b>\n"
        "  /verilerimi_sil — Sistemdeki tüm kayıtlı verilerinizi kalıcı olarak siler."
    )
    await update.message.reply_text(mesaj, parse_mode="HTML")


async def cmd_takvim(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/takvim — Akademik takvimi 3 ayrı mesajda, çift satırlı ve L girintili listeler."""
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT event_name, event_date FROM calendar ORDER BY event_date ASC")
        rows = cur.fetchall()

    if not rows:
        await update.message.reply_text("📅 Takvimde henüz etkinlik bulunmuyor.")
        return

    guz_events = []
    bahar_events = []
    yaz_events = []

    for event_name, event_date in rows:
        formatted_date = format_date_tr(event_date)
        try:
            dt = datetime.datetime.strptime(event_date, "%Y-%m-%d")
            # Çift satırlı ve L girintili premium düzen
            event_line = f"• {formatted_date}\n  L {event_name}"
            
            if dt < datetime.datetime(2026, 2, 6):
                guz_events.append(event_line)
            elif dt < datetime.datetime(2026, 7, 16):
                bahar_events.append(event_line)
            else:
                yaz_events.append(event_line)
        except Exception:
            guz_events.append(f"• {event_date}\n  L {event_name}")

    # Her dönemi tam ekran görüntüsündeki gibi 3 AYRI MESAJ balonunda gönderiyoruz!
    if guz_events:
        guz_msg = "🍁 <b>GÜZ YARIYILI (2025-2026)</b>\n\n" + "\n\n".join(guz_events)
        await update.message.reply_text(guz_msg, parse_mode="HTML")
    
    if bahar_events:
        bahar_msg = "🌸 <b>BAHAR YARIYILI (2025-2026)</b>\n\n" + "\n\n".join(bahar_events)
        await update.message.reply_text(bahar_msg, parse_mode="HTML")
        
    if yaz_events:
        yaz_msg = "☀️ <b>YAZ OKULU DÖNEMİ (2026)</b>\n\n" + "\n\n".join(yaz_events)
        await update.message.reply_text(yaz_msg, parse_mode="HTML")


async def cmd_duyurular(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/duyurular — KOÜ BSM resmi sitesindeki güncel son 20 duyuruyu listeler."""
    await update.message.reply_chat_action("typing")
    
    duyurular = fetch_live_announcements()
    
    if duyurular is None:
        await update.message.reply_text(
            "⚠️ <b>Hata:</b> Kocaeli Üniversitesi duyuru sistemine şu an erişilemiyor.\n"
            "Lütfen birkaç dakika sonra tekrar deneyin.",
            parse_mode="HTML"
        )
        return

    if not duyurular:
        await update.message.reply_text(
            "📢 Bölüme ait güncel bir duyuru bulunamadı.",
            parse_mode="HTML"
        )
        return

    satirlar = ["📢 <b>KOÜ BSM Güncel Duyuruları</b>\n"]
    for i, item in enumerate(duyurular, start=1):
        esc_title = html.escape(item['title'])
        esc_date = html.escape(item['date'])
        esc_link = html.escape(item['link'])
        
        # Şık hiperlink formatı
        satirlar.append(f"{i}. 📅 {esc_date} — <a href=\"{esc_link}\"><b>{esc_title}</b></a>")

    full_message = "\n\n".join(satirlar)
    
    # Telegram mesaj uzunluğu sınırı kontrolü (maks 4096 karakter)
    if len(full_message) > 4000:
        satirlar = satirlar[:15]
        satirlar.append("\n⚠️ <i>Karakter sınırı nedeniyle kalan duyurular listelenemedi.</i>")
        full_message = "\n\n".join(satirlar)

    await update.message.reply_text(
        full_message, 
        parse_mode="HTML",
        disable_web_page_preview=True  # Link önizleme balonlarını kapatarak temiz bir akış sunar
    )


def get_canonical_course(course_name: str) -> tuple[str, int] | None:
    """Ders adına göre standart (canonical) ismi ve devamsızlık limitini döndürür. Listede yoksa None döner."""
    normalized = course_name.lower().strip()
    
    if normalized in ["fizik"]:
        return "Fizik", 999
    elif normalized in ["matematik 2", "matematik"]:
        return "Matematik 2", 4
    elif normalized in ["laboratuvar", "laboratuvar dersi", "lab"]:
        return "Laboratuvar", 3
    elif normalized in ["lineer cebir", "linner cebir", "cebir", "linner cebir dersi"]:
        return "Linner Cebir", 999
    elif normalized in ["türkçe", "turkce", "türkçe dersi"]:
        return "Türkçe", 999
    elif normalized in ["tarih", "tarih dersi", "inkılap tarihi", "ata"]:
        return "Tarih", 999
    elif normalized in ["ingilizce", "ingilizce dersi", "english"]:
        return "İngilizce", 999
    elif normalized in ["algoritma", "algoritma dersi", "algoritmalar"]:
        return "Algoritma", 999
    else:
        return None


async def cmd_devamsizlik_ekle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/devamsizlik_ekle [Ders Adı] — Devamsızlık sayacını 1 artırır."""
    if not context.args:
        # Kullanıcı argümansız çağırdığında derslerin isimlerini ve limitlerini listeler
        mesaj = (
            "<b>Kullanım:</b> <code>/devamsizlik_ekle [Ders Adı]</code>\n"
            "Örnek: <code>/devamsizlik_ekle Matematik 2</code>\n\n"
            "<b>Ders Listesi ve Devamsızlık Limitleri:</b>\n"
            "• <b>Matematik 2</b> — Limit: 4 Hak\n"
            "• <b>Laboratuvar</b> — Limit: 3 Hak\n"
            "• <b>Fizik</b> — Sınırsız (Hoca bakmıyor)\n"
            "• <b>Linner Cebir</b> — Sınırsız (Hoca bakmıyor)\n"
            "• <b>Türkçe</b> — Sınırsız (Hoca bakmıyor)\n"
            "• <b>Tarih</b> — Sınırsız (Hoca bakmıyor)\n"
            "• <b>İngilizce</b> — Sınırsız (Hoca bakmıyor)\n"
            "• <b>Algoritma</b> — Sınırsız (Hoca bakmıyor)\n"
        )
        await update.message.reply_text(mesaj, parse_mode="HTML")
        return

    course_name = " ".join(context.args).strip()

    # Giriş Uzunluğu Kontrolü (Buffer Overflow ve DB DoS Koruması)
    if len(course_name) > 50:
        await update.message.reply_text(
            "Ders adı en fazla 50 karakter uzunluğunda olabilir.",
            parse_mode="HTML"
        )
        return

    canonical_info = get_canonical_course(course_name)
    if not canonical_info:
        mesaj = (
            f"<b>Hata:</b> Girdiğiniz ders adı (<code>{html.escape(course_name)}</code>) geçerli ders listesinde bulunamadı.\n"
            "Lütfen girdiğiniz adı listedekilerden biri olacak şekilde kontrol edip tekrar deneyin.\n\n"
            "<b>Geçerli Dersler:</b>\n"
            "• Matematik 2\n"
            "• Laboratuvar\n"
            "• Fizik\n"
            "• Linner Cebir\n"
            "• Türkçe\n"
            "• Tarih\n"
            "• İngilizce\n"
            "• Algoritma"
        )
        await update.message.reply_text(mesaj, parse_mode="HTML")
        return

    canonical_name, limit = canonical_info
    user_id = update.effective_user.id

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()

        # Ders yoksa oluştur (1 devamsızlık), varsa sayacı artır ve limiti güncelle
        cur.execute("""
            INSERT INTO attendance (user_id, course_name, absent_count, max_limit)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(user_id, course_name)
            DO UPDATE SET absent_count = absent_count + 1, max_limit = ?
        """, (user_id, canonical_name, limit, limit))

        # Güncel durumu oku
        cur.execute(
            "SELECT absent_count, max_limit FROM attendance WHERE user_id=? AND course_name=?",
            (user_id, canonical_name),
        )
        absent_count, max_limit = cur.fetchone()
        conn.commit()

    esc_course = html.escape(canonical_name)
    
    if max_limit >= 999:
        mesaj = (
            f"<b>{esc_course}</b> dersi devamsızlığın güncellendi.\n"
            f"Mevcut: {absent_count} / Sınırsız (Hoca bakmıyor)"
        )
    else:
        mesaj = (
            f"<b>{esc_course}</b> dersi devamsızlığın güncellendi.\n"
            f"Mevcut: {absent_count} / {max_limit}"
        )
        if absent_count >= max_limit:
            mesaj += (
                f"\n\n<b>DİKKAT</b> Bu ders için devamsızlık sınırını "
                f"({max_limit}) aştın veya sınırdasın."
            )

    await update.message.reply_text(mesaj, parse_mode="HTML")


async def cmd_devamsizlik_durum(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/devamsizlik_durum — Tüm devamsızlıkları listeler."""
    user_id = update.effective_user.id

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT course_name, absent_count, max_limit FROM attendance WHERE user_id=? ORDER BY course_name",
            (user_id,),
        )
        rows = cur.fetchall()

    if not rows:
        await update.message.reply_text("Henüz devamsızlık kaydın bulunmuyor.")
        return

    satirlar = ["<b>Devamsızlık Durumu</b>\n"]
    for course_name, absent_count, max_limit in rows:
        esc_course = html.escape(course_name)
        if max_limit >= 999:
            satirlar.append(f"• <b>{esc_course}</b>: {absent_count} / Sınırsız (Hoca bakmıyor)")
        else:
            durum = " (Sınırda)" if absent_count >= max_limit else ""
            satirlar.append(f"• <b>{esc_course}</b>: {absent_count} / {max_limit}{durum}")

    await update.message.reply_text("\n".join(satirlar), parse_mode="HTML")


async def cmd_devamsizlik_sil(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/devamsizlik_sil [Ders Adı] — Belirtilen dersin devamsızlık sayısını 1 azaltır."""
    if not context.args:
        # Kullanıcı argümansız çağırdığında derslerin isimlerini listeler
        mesaj = (
            "<b>Kullanım:</b> <code>/devamsizlik_sil [Ders Adı]</code>\n"
            "Örnek: <code>/devamsizlik_sil Matematik 2</code>\n\n"
            "<b>Geçerli Dersler:</b>\n"
            "• Matematik 2\n"
            "• Laboratuvar\n"
            "• Fizik\n"
            "• Linner Cebir\n"
            "• Türkçe\n"
            "• Tarih\n"
            "• İngilizce\n"
            "• Algoritma"
        )
        await update.message.reply_text(mesaj, parse_mode="HTML")
        return

    course_name = " ".join(context.args).strip()

    # Giriş Uzunluğu Kontrolü
    if len(course_name) > 50:
        await update.message.reply_text(
            "Ders adı en fazla 50 karakter uzunluğunda olabilir.",
            parse_mode="HTML"
        )
        return

    canonical_info = get_canonical_course(course_name)
    if not canonical_info:
        mesaj = (
            f"<b>Hata:</b> Girdiğiniz ders adı (<code>{html.escape(course_name)}</code>) geçerli ders listesinde bulunamadı.\n"
            "Lütfen girdiğiniz adı listedekilerden biri olacak şekilde kontrol edip tekrar deneyin.\n\n"
            "<b>Geçerli Dersler:</b>\n"
            "• Matematik 2\n"
            "• Laboratuvar\n"
            "• Fizik\n"
            "• Linner Cebir\n"
            "• Türkçe\n"
            "• Tarih\n"
            "• İngilizce\n"
            "• Algoritma"
        )
        await update.message.reply_text(mesaj, parse_mode="HTML")
        return

    canonical_name, limit = canonical_info
    user_id = update.effective_user.id

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        
        # Öncelikle bu ders için devamsızlık kaydı var mı kontrol et
        cur.execute(
            "SELECT absent_count, max_limit FROM attendance WHERE user_id=? AND course_name=?",
            (user_id, canonical_name)
        )
        row = cur.fetchone()
        
        if not row:
            await update.message.reply_text(
                f"<b>{html.escape(canonical_name)}</b> dersi için zaten kayıtlı bir devamsızlığınız bulunmamaktadır.",
                parse_mode="HTML"
            )
            return
            
        absent_count, max_limit = row
        
        if absent_count <= 0:
            await update.message.reply_text(
                f"<b>{html.escape(canonical_name)}</b> dersi devamsızlığınız zaten 0 gündür, daha fazla azaltılamaz.",
                parse_mode="HTML"
            )
            return
            
        new_count = absent_count - 1
        
        cur.execute(
            "UPDATE attendance SET absent_count=? WHERE user_id=? AND course_name=?",
            (new_count, user_id, canonical_name)
        )
        conn.commit()

    esc_course = html.escape(canonical_name)
    
    if max_limit >= 999:
        mesaj = (
            f"<b>{esc_course}</b> dersi devamsızlığınız 1 azaltıldı.\n"
            f"Yeni Durum: {new_count} / Sınırsız (Hoca bakmıyor)"
        )
    else:
        mesaj = (
            f"<b>{esc_course}</b> dersi devamsızlığınız 1 azaltıldı.\n"
            f"Yeni Durum: {new_count} / {max_limit}"
        )
        
    await update.message.reply_text(mesaj, parse_mode="HTML")


async def cmd_not_ekle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/not_ekle [Ders Adı] [Vize] [Final] — Not ekler veya günceller."""
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "⚠️ Kullanım: /not_ekle [Ders Adı] [Vize] [Final]\n"
            "Örnek: /not_ekle Matematik 70 85",
            parse_mode="HTML"
        )
        return

    args = context.args

    # Son iki argüman notlar, geri kalanı ders adı
    try:
        final_notu = float(args[-1])
        vize_notu = float(args[-2])
    except ValueError:
        await update.message.reply_text(
            "❌ Vize ve Final değerleri sayı olmalıdır.\n"
            "Örnek: /not_ekle Matematik 70 85",
            parse_mode="HTML"
        )
        return

    # Geçerli not aralığı kontrolü
    if not (0 <= vize_notu <= 100 and 0 <= final_notu <= 100):
        await update.message.reply_text("❌ Notlar 0 ile 100 arasında olmalıdır.", parse_mode="HTML")
        return

    course_name = " ".join(args[:-2]).strip()
    if not course_name:
        await update.message.reply_text("❌ Ders adı boş olamaz.", parse_mode="HTML")
        return

    # Giriş Uzunluğu Kontrolü
    if len(course_name) > 50:
        await update.message.reply_text(
            "⚠️ Ders adı en fazla 50 karakter uzunluğunda olabilir.",
            parse_mode="HTML"
        )
        return

    user_id = update.effective_user.id

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO grades (user_id, course_name, midterm, final)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, course_name)
            DO UPDATE SET midterm = excluded.midterm,
                          final   = excluded.final
        """, (user_id, course_name, vize_notu, final_notu))
        conn.commit()

    esc_course = html.escape(course_name)
    await update.message.reply_text(
        f"✅ <b>{esc_course}</b> dersi notları kaydedildi.\n"
        f"Vize: {vize_notu}  |  Final: {final_notu}",
        parse_mode="HTML",
    )


async def cmd_not_durum(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/not_durum — Notları ve geçme durumunu listeler."""
    user_id = update.effective_user.id

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT course_name, midterm, final FROM grades WHERE user_id=? ORDER BY course_name",
            (user_id,),
        )
        rows = cur.fetchall()

    if not rows:
        await update.message.reply_text("📝 Henüz not kaydın bulunmuyor.")
        return

    satirlar = ["📝 <b>Not Durumu</b>\n"]
    for course_name, midterm, final in rows:
        esc_course = html.escape(course_name)
        if midterm is None or final is None:
            satirlar.append(f"<b>{esc_course}</b>\n  Henüz not girilmemiş.")
            continue
        ortalama = (midterm * 0.4) + (final * 0.6)
        sonuc = "Geçti ✅" if ortalama >= 50 else "Kaldı ❌"
        satirlar.append(
            f"<b>{esc_course}</b>\n"
            f"  Vize: {midterm:.1f}  |  Final: {final:.1f}  |  Ort: {ortalama:.1f}  →  {sonuc}"
        )

    await update.message.reply_text("\n\n".join(satirlar), parse_mode="HTML")


async def cmd_arsiv_ekle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/arsiv_ekle [Ders Adı] [Link/İçerik] — Materyal kaydeder."""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ Kullanım: /arsiv_ekle [Ders Adı] [Link veya İçerik]\n"
            "Örnek: /arsiv_ekle Matematik https://example.com/notlar",
            parse_mode="HTML"
        )
        return

    course_name = context.args[0].strip()
    link_or_text = " ".join(context.args[1:]).strip()

    # Giriş Uzunluğu Kontrolleri
    if len(course_name) > 50:
        await update.message.reply_text(
            "⚠️ Ders adı en fazla 50 karakter uzunluğunda olabilir.",
            parse_mode="HTML"
        )
        return

    if len(link_or_text) > 500:
        await update.message.reply_text(
            "⚠️ İçerik veya Link en fazla 500 karakter uzunluğunda olabilir.",
            parse_mode="HTML"
        )
        return

    user_id = update.effective_user.id

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO materials (user_id, course_name, link_or_text) VALUES (?, ?, ?)",
            (user_id, course_name, link_or_text),
        )
        conn.commit()

    esc_course = html.escape(course_name)
    await update.message.reply_text(
        f"✅ <b>{esc_course}</b> dersi için materyal kaydedildi.",
        parse_mode="HTML",
    )


async def cmd_arsiv_getir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/arsiv_getir — Kayıtlı materyalleri listeler."""
    user_id = update.effective_user.id

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT course_name, link_or_text FROM materials WHERE user_id=? ORDER BY course_name",
            (user_id,),
        )
        rows = cur.fetchall()

    if not rows:
        await update.message.reply_text("📁 Henüz materyal kaydın bulunmuyor.")
        return

    satirlar = ["📁 <b>Materyal Arşivi</b>\n"]
    for i, (course_name, link_or_text) in enumerate(rows, start=1):
        esc_course = html.escape(course_name)
        esc_content = html.escape(link_or_text)
        satirlar.append(f"{i}. <b>{esc_course}</b>\n   {esc_content}")

    await update.message.reply_text("\n\n".join(satirlar), parse_mode="HTML")


async def cmd_verilerimi_sil(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/verilerimi_sil — Kullanıcının tüm verilerini siler (KVKK uyumluluğu)."""
    user_id = update.effective_user.id

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        # Üç tablodan da kullanıcının kayıtlarını sil
        cur.execute("DELETE FROM attendance WHERE user_id=?", (user_id,))
        cur.execute("DELETE FROM grades WHERE user_id=?", (user_id,))
        cur.execute("DELETE FROM materials WHERE user_id=?", (user_id,))
        conn.commit()

    mesaj = (
        "🗑️ <b>Verileriniz Başarıyla Silindi</b>\n\n"
        "Kişisel Verilerin Korunması Kanunu (KVKK) uyumluluğu kapsamında, "
        "öğrenci asistanı botu veritabanında adınıza kayıtlı olan tüm not, "
        "devamsızlık ve materyal arşivi verileri sistemden <b>kalıcı olarak silinmiştir</b>."
    )
    await update.message.reply_text(mesaj, parse_mode="HTML")


# ---------------------------------------------------------------------------
# Asenkron Başlatıcı Kancası (Telegram / Menü komutlarını tescil eder)
# ---------------------------------------------------------------------------

async def post_init(application: Application) -> None:
    """Uygulama başlatılırken Telegram üzerindeki / menüsü komutlarını kaydeder."""
    commands = [
        BotCommand("start", "Karşılama mesajı ve komut rehberi"),
        BotCommand("takvim", "Akademik takvimi listeler"),
        BotCommand("duyurular", "Resmi son 20 canlı BSM duyurusunu listeler"),
        BotCommand("devamsizlik_ekle", "Ders adı girerek devamsızlık ekler"),
        BotCommand("devamsizlik_sil", "Ders devamsızlık sayısını 1 azaltır"),
        BotCommand("devamsizlik_durum", "Mevcut devamsızlık durumunu gösterir"),
        BotCommand("not_ekle", "Ders notlarını ekler/günceller"),
        BotCommand("not_durum", "Notlarınızı ve geçme durumunu listeler"),
        BotCommand("arsiv_ekle", "Derse ait materyal/link arşivler"),
        BotCommand("arsiv_getir", "Kayıtlı materyal arşivini listeler"),
        BotCommand("verilerimi_sil", "Tüm bot verilerinizi kalıcı olarak siler (KVKK)")
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Telegram / menü komutları başarıyla tescil edildi.")


# ---------------------------------------------------------------------------
# Uygulama Giriş Noktası
# ---------------------------------------------------------------------------

def main() -> None:
    if not BOT_TOKEN:
        logger.critical(
            "BOT_TOKEN ortam değişkeni ayarlanmamış! "
            "Örnek: export BOT_TOKEN='123456:ABC-DEF...'"
        )
        raise SystemExit(1)

    # Veritabanını başlat
    setup_database()

    # Uygulamayı oluştur (post_init kancası ile)
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Komut işleyicilerini kaydet
    app.add_handler(CommandHandler("start",               cmd_start))
    app.add_handler(CommandHandler("takvim",              cmd_takvim))
    app.add_handler(CommandHandler("duyurular",           cmd_duyurular))
    app.add_handler(CommandHandler("devamsizlik_ekle",    cmd_devamsizlik_ekle))
    app.add_handler(CommandHandler("devamsizlik_sil",     cmd_devamsizlik_sil))
    app.add_handler(CommandHandler("devamsizlik_durum",   cmd_devamsizlik_durum))
    app.add_handler(CommandHandler("not_ekle",            cmd_not_ekle))
    app.add_handler(CommandHandler("not_durum",           cmd_not_durum))
    app.add_handler(CommandHandler("arsiv_ekle",          cmd_arsiv_ekle))
    app.add_handler(CommandHandler("arsiv_getir",         cmd_arsiv_getir))
    app.add_handler(CommandHandler("verilerimi_sil",      cmd_verilerimi_sil))

    logger.info("Bot başlatılıyor... (Ctrl+C ile durdur)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()