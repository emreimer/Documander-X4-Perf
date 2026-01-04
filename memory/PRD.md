# Documander - Fatura Yönetim Platformu PRD

## Proje Özeti
Muhasebeciler için Wix website'ına gömülebilen fatura yönetim platformu. Kullanıcılar müşteri faturalarını (PDF, JPG, XML, HTML) yükler, AI verileri çıkarır ve "Gelir/Gider" olarak kategorize eder.

## Hedef Kullanıcılar
- Muhasebeciler ve mali müşavirler
- Küçük/orta ölçekli işletme sahipleri
- Serbest çalışan profesyoneller

## Temel Özellikler

### ✅ Tamamlanan Özellikler

#### 1. Wix Entegrasyonu
- URL parametreleri ile oturum başlatma (wixMemberId, plan, expires)
- Webhook ile otomatik plan senkronizasyonu
- Iframe içinde güvenli çalışma

#### 2. Abonelik Sistemi
- 12 aylık planlar (yıllık kota, aylık sıfırlama yok)
- Çoklu paket desteği (kullanıcılar birden fazla plan satın alabilir)
- Deneme paketi: 20 fatura, 7 gün
- Planlar: Başlangıç (1000), Profesyonel (2500), İşletme (5000), Kurumsal (10000)

#### 3. Fatura Yönetimi
- Gelir/Gider kategorileri
- AI ile otomatik veri çıkarma (Gemini 2.5 Flash)
- Tek dosyada birden fazla fiş desteği
- Tarih doğrulama (dönem kontrolü)
- Excel dışa aktarma (Gelir, Gider, Tümü)

#### 4. Admin Paneli (/admin)
- Tüm kullanıcıların listesi
- Kullanıcı iletişim bilgileri (ad, e-posta)
- Paket detayları ve kullanım durumu
- Test kullanıcısı silme özelliği

#### 5. KDV (VAT) Raporu - YENİ ✅
- **KDV Detay Tablosu - Gelir:** Fatura No, Tarih, Müşteri, VKN, V.Dairesi, Açıklama, KDV %, Matrah, KDV Tutarı, Tevkifat
- **KDV Detay Tablosu - Gider:** Fatura No, Tarih, Düzenleyen, VKN, V.Dairesi, Açıklama, KDV %, Matrah, KDV Tutarı, Tevkifat
- **KDV Özet Raporu:** KDV oranlarına göre (%1, %10, %20) Gelir/Gider matrah ve KDV toplamları, Net KDV
- **Hesaplama Kutusu:** Hesaplanan KDV (Gelir) - İndirilecek KDV (Gider) = Ödenecek/Devreden KDV

#### 6. UI/UX İyileştirmeleri
- Tam ekran "İşleniyor" overlay'i
- Birleşik "Sonuç" overlay'i (uyarılar, hatalar)
- Çoklu paket gösterimi
- Kota uyarıları

### 🔄 Devam Eden

#### Domain Kısıtlaması
- **Durum:** Geçici olarak devre dışı (preview için)
- **Yeniden aktifleştirme:** Deployment öncesi `/app/frontend/src/App.js` ve `/app/backend/server.py` dosyalarındaki yorumları kaldır

### 📋 Gelecek Görevler (Backlog)

#### P1 - Yüksek Öncelik
1. **Gerçek AI Entegrasyonu:** Mock fonksiyonu GPT-4o Vision ile değiştir
2. **Luca Uyumlu Excel:** Kullanıcıdan şablon bekleniyoe

#### P2 - Orta Öncelik
1. **Kod Refactoring:**
   - `server.py` → routes/, models/, services/ yapısına ayır
   - `DashboardPage.js` → Ayrı bileşenlere böl (InvoiceTable, VatReport vs.)

#### P3 - Düşük Öncelik
1. Fatura düzenleme geçmişi
2. Raporları PDF olarak indirme
3. Çoklu dil desteği

## Teknik Mimari

### Backend (FastAPI)
- `/app/backend/server.py` - Ana API dosyası
- MongoDB veritabanı
- Emergent LLM entegrasyonu (Gemini 2.5 Flash)

### Frontend (React)
- `/app/frontend/src/pages/DashboardPage.js` - Ana kullanıcı arayüzü
- `/app/frontend/src/pages/AdminPage.js` - Admin paneli
- Shadcn/UI bileşenleri

### Veritabanı Şeması
- `subscriptions`: Kullanıcı abonelikleri ve paketler
- `users`: Kullanıcı bilgileri
- `invoices`: Fatura verileri (vat_details dahil)
- `taxpayer_sessions`: Mükellef oturumları

## API Endpoints

### Kullanıcı
- `GET /api/sessions/current` - Mevcut oturum
- `POST /api/sessions` - Yeni oturum oluştur
- `GET /api/subscription/status` - Abonelik durumu

### Faturalar
- `POST /api/invoices/upload` - Fatura yükle
- `GET /api/invoices` - Faturaları listele
- `GET /api/invoices/vat-report` - KDV raporu
- `GET /api/invoices/export/excel` - Excel indir

### Admin
- `GET /api/admin/users` - Tüm kullanıcılar
- `DELETE /api/admin/users/{id}` - Kullanıcı sil

### Webhook
- `POST /api/webhook/wix/new-order` - Wix sipariş webhook

## Güncelleme Geçmişi

### 2026-01-04
- ✅ KDV Raporu özelliği tamamlandı
- ✅ Gelir/Gider ayrı tablolar eklendi
- ✅ KDV özet raporu ve hesaplama kutusu eklendi
- ✅ Preview erişimi için domain kısıtlaması geçici olarak kaldırıldı

### Önceki Güncellemeler
- Çoklu paket abonelik sistemi
- Admin paneli ve kullanıcı yönetimi
- Wix webhook entegrasyonu
- UI overlay'leri (işleniyor/sonuç)
