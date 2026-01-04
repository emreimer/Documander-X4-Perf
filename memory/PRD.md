# Documander - Fatura Yönetim Platformu PRD

## Proje Özeti
Muhasebeciler için Wix website'ına gömülebilen fatura yönetim platformu. Kullanıcılar müşteri faturalarını (PDF, JPG, XML, HTML) yükler, AI verileri çıkarır ve "Gelir/Gider" olarak kategorize eder.

## Temel Özellikler

### ✅ Tamamlanan Özellikler

#### 1. Wix Entegrasyonu
- URL parametreleri ile oturum başlatma
- Webhook ile otomatik plan senkronizasyonu
- Iframe içinde güvenli çalışma

#### 2. Abonelik Sistemi
- 12 aylık planlar (yıllık kota)
- Çoklu paket desteği
- Deneme paketi: 20 fatura, 7 gün

#### 3. Fatura Yönetimi
- Gelir/Gider kategorileri
- **AI ile otomatik veri çıkarma (GPT-4o Vision)** ✅
- Tek dosyada birden fazla fiş desteği
- Excel dışa aktarma

#### 4. Admin Paneli (/admin)
- Tüm kullanıcıların listesi
- Kullanıcı iletişim bilgileri
- Paket detayları ve kullanım durumu

#### 5. KDV (VAT) Raporu ✅
**Detay Tabloları:**
- KDV Detay Tablosu - Gelir: Fatura No, Tarih, Müşteri, VKN, V.Dairesi, Açıklama, KDV %, Matrah, KDV Tutarı
- KDV Detay Tablosu - Gider: Fatura No, Tarih, Düzenleyen, VKN, V.Dairesi, Açıklama, KDV %, Matrah, KDV Tutarı
- **Tevkifat sütunu kaldırıldı** ✅

**Özet Tabloları (3 ayrı tablo):** ✅
- KDV Özet Raporu - Gelir
- KDV Özet Raporu - Gider
- KDV Özet Raporu - [Dönem] Dönemi Net (örn: "Ocak 2026 Dönemi Net")

**Excel İndirme:** ✅
- Her KDV tablosu için ayrı Excel indirme butonu (Gelir, Gider)
- Tümünü Excel İndir → 2 sheet'li dosya:
  - Sheet 1: "Gelir-Gider" (faturalar)
  - Sheet 2: "KDV Raporu" (KDV detay ve özet)

### 🔄 Geçici Durum
- Domain kısıtlaması preview için devre dışı (deployment öncesi aktifleştirilmeli)

### 📋 Gelecek Görevler

#### P1 - Yüksek Öncelik
1. Luca Uyumlu Excel (şablon bekleniyor)

#### P2 - Orta Öncelik
1. Kod refactoring (server.py ve DashboardPage.js modüllere ayırma)

## Teknik Mimari
- Backend: FastAPI + MongoDB
- Frontend: React + Shadcn/UI
- AI: **OpenAI GPT-4o Vision** (Emergent LLM Key ile)

## API Endpoints

### KDV Raporu
- `GET /api/invoices/vat-report` - KDV raporu JSON
- `GET /api/invoices/vat-report/excel` - KDV raporu Excel
- `GET /api/invoices/vat-report/excel?category=income` - Sadece Gelir KDV Excel
- `GET /api/invoices/vat-report/excel?category=expense` - Sadece Gider KDV Excel

## Güncelleme Geçmişi

### 2026-01-04
- ✅ AI entegrasyonu: Gemini 2.5 Flash → GPT-4o Vision
- ✅ KDV tablolarından tevkifat sütunu kaldırıldı
- ✅ Her KDV tablosu için Excel indirme butonu eklendi
- ✅ Ana Excel export 2 sheet'li yapıldı (Gelir-Gider, KDV Raporu)
- ✅ KDV Özet Raporu 3 ayrı tabloya ayrıldı (Gelir, Gider, Net)
- ✅ Dönem bilgisi Net tablo başlığına eklendi
