# Documander - Fatura Yönetim Platformu PRD

## Proje Özeti
Muhasebeciler için Wix website'ına gömülebilen fatura yönetim platformu.

## ✅ Tamamlanan Özellikler

### 1. Fatura Yönetimi
- Gelir/Gider kategorileri
- **AI ile otomatik veri çıkarma (GPT-4o Vision)**
- Excel dışa aktarma

### 2. KDV (VAT) Raporu
**Detay Tabloları:**
- KDV Detay Tablosu - Gelir (+ Excel İndir)
- KDV Detay Tablosu - Gider (+ Excel İndir)

**Özet Tabloları (her biri ayrı Excel butonlu):**
- KDV Özet Raporu - Gelir (+ Excel İndir)
- KDV Özet Raporu - Gider (+ Excel İndir)
- KDV Özet Raporu - [Dönem] Dönemi Net (+ Excel İndir)

### 3. Excel Export (7 Sheet)
**"Tümünü İndir" butonu ile 7 ayrı sheet:**
1. **Gelir Faturaları**
2. **Gider Faturaları**
3. **KDV Detay - Gelir**
4. **KDV Detay - Gider**
5. **KDV Özet - Gelir**
6. **KDV Özet - Gider**
7. **KDV Özet - Net**

**Sütun genişlikleri otomatik ayarlanıyor (metinler tam sığıyor)**

### 4. Diğer Özellikler
- Wix entegrasyonu (URL params + webhook)
- 12 aylık çoklu paket abonelik sistemi
- Admin paneli (/admin)
- Deneme paketi: 20 fatura, 7 gün

### 🔄 Geçici Durum
- Domain kısıtlaması preview için devre dışı

### 📋 Gelecek Görevler
1. 🟡 Luca Uyumlu Excel (şablon bekleniyor)
2. Kod refactoring

## Güncelleme Geçmişi

### 2026-01-04
- ✅ KDV Özet sheet'i 3 ayrı sheet'e ayrıldı (Gelir, Gider, Net)
- ✅ Her KDV tablosuna ayrı Excel İndir butonu eklendi (5 buton)
- ✅ Excel sütun genişlikleri otomatik ayarlanıyor
- ✅ AI entegrasyonu: GPT-4o Vision
- ✅ Toplam 7 sheet'li Excel export
