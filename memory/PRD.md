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
- AI ile otomatik veri çıkarma (MOCK - Gemini 2.5 Flash hazır)
- Tek dosyada birden fazla fiş desteği
- Excel dışa aktarma

#### 4. Admin Paneli (/admin)
- Tüm kullanıcıların listesi
- Kullanıcı iletişim bilgileri
- Paket detayları ve kullanım durumu

#### 5. KDV (VAT) Raporu ✅
**Detay Tabloları:**
- KDV Detay Tablosu - Gelir: Fatura No, Tarih, Müşteri, VKN, V.Dairesi, Açıklama, KDV %, Matrah, KDV Tutarı, Tevkifat
- KDV Detay Tablosu - Gider: Fatura No, Tarih, Düzenleyen, VKN, V.Dairesi, Açıklama, KDV %, Matrah, KDV Tutarı, Tevkifat

**Özet Tabloları (3 ayrı tablo):**
- KDV Özet Raporu - Gelir: KDV oranlarına göre (%1, %10, %20) Matrah ve KDV toplamları
- KDV Özet Raporu - Gider: KDV oranlarına göre (%1, %10, %20) Matrah ve KDV toplamları
- KDV Özet Raporu - [Dönem] Dönemi Net: Hesaplanan KDV, İndirilecek KDV, Net KDV ve Ödenecek/Devreden KDV özeti

### 🔄 Geçici Durum
- Domain kısıtlaması preview için devre dışı (deployment öncesi aktifleştirilmeli)

### 📋 Gelecek Görevler

#### P1 - Yüksek Öncelik
1. Gerçek AI Entegrasyonu (Mock → GPT-4o Vision)
2. Luca Uyumlu Excel (şablon bekleniyor)

#### P2 - Orta Öncelik
1. KDV Raporunu Excel olarak indirme
2. Kod refactoring

## Teknik Mimari
- Backend: FastAPI + MongoDB
- Frontend: React + Shadcn/UI
- AI: Emergent LLM (Gemini 2.5 Flash)

## Güncelleme Geçmişi

### 2026-01-04
- ✅ KDV Özet Raporu 3 ayrı tabloya bölündü (Gelir, Gider, Net)
- ✅ Dönem bilgisi Net tablo başlığına eklendi
- ✅ Preview erişimi açıldı
