# 🎓 Öğrenci Asistanı Telegram Botu — Komut ve Çıktı Kılavuzu

Bu belge, KOÜ BSM Öğrenci Asistanı Telegram Botu içerisinde yer alan tüm komutları, bu komutların kabul ettiği parametreleri (girdileri), çalışma mantıklarını ve üretilen örnek çıktı mesajlarını listeler.

---

## 📋 Genel Komut Listesi ve Özet Tablo

| Komut | Açıklama | Girdi (Parametre) | Çıktı Tipi / Davranış |
| :--- | :--- | :--- | :--- |
| **`/start`** | Karşılama mesajı ve komut rehberi | Yok | HTML zengin komut rehber mesajı |
| **`/takvim`** | KOÜ Resmi Akademik Takvimi | Yok | Dönemlere göre bölünmüş 3 ayrı mesaj |
| **`/duyurular`** | Canlı KOÜ BSM Duyuruları | Yok | Tıklanabilir son 20 duyuru başlığı |
| **`/devamsizlik_ekle`**| Derse 1 gün devamsızlık ekler | `[Ders Adı]` | Limit/Sınır durumu güncel gösterimi |
| **`/devamsizlik_sil`** | Dersten 1 gün devamsızlık siler | `[Ders Adı]` | Azaltılmış güncel durum gösterimi |
| **`/devamsizlik_durum`**| Tüm devamsızlık özetini listeler| Yok | Liste formatında limitli/limitsiz durum |
| **`/not_ekle`** | Derse Vize ve Final notu ekler | `[Ders] [Vize] [Final]` | Not kaydı onay mesajı |
| **`/not_durum`** | Notları ve geçme durumlarını listeler| Yok | Ortalama hesabı ve Geçti/Kaldı ikonu |
| **`/arsiv_ekle`** | Derse ait ders notu/link kaydeder| `[Ders] [Link/Metin]` | Materyal arşivi onay mesajı |
| **`/arsiv_getir`** | Kayıtlı tüm materyalleri listeler | Yok | Numaralandırılmış ders materyalleri |
| **`/verilerimi_sil`** | KVKK kapsamında tüm verileri siler | Yok | Kalıcı veri silme ve yasal onay metni |

---

## 🔍 Detaylı Komut İncelemeleri ve Örnek Çıktılar

### 1. `/start`
*   **Amaç:** Kullanıcıyı karşılar ve botun tüm yeteneklerini tanıtır.
*   **Örnek Çıktı:**
    > 👋 Merhaba, **Umut**! Ben Öğrenci Asistanı Botuyum.
    >
    > Kullanabileceğin komutlar:
    >
    > 📅 **Akademik Takvim**
    >   /takvim — Akademik etkinlikleri listeler.
    >
    > 📢 **Canlı Duyurular**
    >   /duyurular — Son 20 canlı BSM duyurusunu listeler.
    > ... *(diğer komut listesi)*

---

### 2. `/takvim`
*   **Amaç:** KOÜ 2025-2026 Akademik Takvimi verilerini Güz, Bahar ve Yaz Okulu olmak üzere 3 farklı mesaj balonunda, çift satırlı ve premium `L` girintisiyle listeler.
*   **Örnek Çıktı (Bahar Dönemi Balonu):**
    > 🌸 **BAHAR YARIYILI (2025-2026)**
    >
    > • 16 Şubat 2026, Pazartesi
    >   L 🏫 Bahar Dönemi Derslerin Başlangıcı
    >
    > • 13 Nisan 2026, Pazartesi
    >   L 📝 Bahar Dönemi Ara Sınavları (Vizeler) Başlangıcı
    >
    > • 17 Nisan 2026, Cuma
    >   L 📝 Bahar Dönemi Ara Sınavları (Vizeler) Sonu

---

### 3. `/duyurular`
*   **Amaç:** Kocaeli Üniversitesi Bilgisayar Mühendisliği (BSM) resmi API sunucusundan son 20 duyuruyu çeker, 5 dakikalık akıllı önbellek mekanizmasıyla sunucuyu yormadan tıklanabilir HTML formatında listeler.
*   **Örnek Çıktı:**
    > 📢 **KOÜ BSM Güncel Duyuruları**
    >
    > 1. 📅 18.05.2026 — [**Yaz Okulu Ders Programı Hakkında**](https://bilisim.kocaeli.edu.tr/tr/duyurular/yaz-okulu-ders-programi)
    > 2. 📅 12.05.2026 — [**Staj Defteri Teslim Tarihleri Açıklandı**](https://bilisim.kocaeli.edu.tr/tr/duyurular/staj-defteri-teslim)

---

### 4. `/devamsizlik_ekle [Ders Adı]`
*   **Girdi:** Ders adı veya kısaltması (Örn: `matematik 2`, `math`, `lab`, `fizik`, `lineer cebir`, `tarih`).
*   **Çalışma Şekli:** Büyük/küçük harf duyarsız eşleştirme yapar. Parametresiz çağrılırsa geçerli dersleri ve limit kurallarını listeler.
*   **Örnek Çıktı (Parametresiz):**
    > **Kullanım:** `/devamsizlik_ekle [Ders Adı]`
    > Örnek: `/devamsizlik_ekle Matematik 2`
    >
    > **Ders Listesi ve Devamsızlık Limitleri:**
    > • **Matematik 2** — Limit: 4 Hak
    > • **Laboratuvar** — Limit: 3 Hak
    > • **Fizik** — Hoca devamsızlığı önemsemiyor
    > • **Lineer Cebir** — Hoca devamsızlığı önemsemiyor
    > ...
*   **Örnek Çıktı (Limitli - Başarılı):**
    > **Matematik 2** dersi devamsızlığın güncellendi.
    > Mevcut: 2 / 4
*   **Örnek Çıktı (Limitsiz - Başarılı):**
    > **Lineer Cebir** dersi devamsızlığın güncellendi.
    > Mevcut: 1 / Sınırsız (Hoca bakmıyor)
*   **Örnek Çıktı (Hatalı Ders Girildiğinde):**
    > <b>Hata:</b> Girdiğiniz ders adı (`kimya`) geçerli ders listesinde bulunamadı.
    > Lütfen girdiğiniz adı listedekilerden biri olacak şekilde kontrol edip tekrar deneyin.

---

### 5. `/devamsizlik_sil [Ders Adı]`
*   **Amaç:** Eklenen devamsızlığı 1 gün azaltır. Devamsızlık 0'ın altına inemez.
*   **Örnek Çıktı:**
    > **Matematik 2** dersi devamsızlığınız 1 azaltıldı.
    > Yeni Durum: 1 / 4

---

### 6. `/devamsizlik_durum`
*   **Amaç:** Kullanıcının veritabanında kayıtlı olan tüm ders devamsızlıklarını toplu bir liste halinde gösterir. Sınırı aşan veya sınıra ulaşan derslerin yanına otomatik `(Sınırda)` uyarısı ekler.
*   **Örnek Çıktı:**
    > **Devamsızlık Durumu**
    > • **Matematik 2**: 4 / 4 (Sınırda)
    > • **Laboratuvar**: 1 / 3
    > • **Lineer Cebir**: 2 / Sınırsız (Hoca bakmıyor)

---

### 7. `/not_ekle [Ders Adı] [Vize] [Final]`
*   **Girdi:** Ders adı, vize notu ve final notu (Örn: `/not_ekle Matematik 2 75 90`).
*   **Çalışma Şekli:** Girilen notların 0-100 arasında sayısal değerler olduğunu doğrular ve veritabanına kaydeder/günceller.
*   **Örnek Çıktı:**
    > ✅ **Matematik 2** dersi notları kaydedildi.
    > Vize: 75.0  |  Final: 90.0

---

### 8. `/not_durum`
*   **Amaç:** Kayıtlı notları listeler. KOÜ BSM yönetmeliğine uygun olarak vizenin **%40**'ını ve finalin **%60**'ını alarak ortalama hesaplar. Geçme notu **50** barajına göre dersin yanına `Geçti ✅` veya `Kaldı ❌` durumunu ekler.
*   **Örnek Çıktı:**
    > 📝 **Not Durumu**
    >
    > **Matematik 2**
    >   Vize: 75.0  |  Final: 90.0  |  Ort: 84.0  →  Geçti ✅
    >
    > **Laboratuvar**
    >   Vize: 40.0  |  Final: 45.0  |  Ort: 43.0  →  Kaldı ❌

---

### 9. `/arsiv_ekle [Ders Adı] [Link/İçerik]`
*   **Girdi:** Tek kelimelik ders adı ve ardından kaydedilecek link veya metin. (Örn: `/arsiv_ekle Matematik https://drive.google.com/...`).
*   **Örnek Çıktı:**
    > ✅ **Matematik** dersi için materyal kaydedildi.

---

### 10. `/arsiv_getir`
*   **Amaç:** Kullanıcının kaydettiği tüm ders çalışma materyallerini, slaytları ve PDF bağlantılarını listeler.
*   **Örnek Çıktı:**
    > 📁 **Materyal Arşivi**
    >
    > 1. **Matematik**
    >    https://drive.google.com/drive/folders/math-notes
    > 2. **Fizik**
    >    1. Vize Sınav Soruları Çözümü PDF linki

---

### 11. `/verilerimi_sil`
*   **Amaç:** KVKK uyumluluğu kapsamında kullanıcının veritabanında barındırdığı not, devamsızlık ve arşiv materyallerinin tamamını tek bir tuşla kalıcı ve geri döndürülemez şekilde siler.
*   **Örnek Çıktı:**
    > 🗑️ **Verileriniz Başarıyla Silindi**
    >
    > Kişisel Verilerin Korunması Kanunu (KVKK) uyumluluğu kapsamında, öğrenci asistanı botu veritabanında adınıza kayıtlı olan tüm not, devamsızlık ve materyal arşivi verileri sistemden **kalıcı olarak silinmiştir**.
