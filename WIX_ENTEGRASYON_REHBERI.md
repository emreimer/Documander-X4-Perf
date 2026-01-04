# Documander - Wix Entegrasyon Rehberi

## 1. Wix Velo ile Member ID'yi iframe'e Aktarma

### Adım 1: Wix Editor'da Velo'yu Aktifleştirin
1. Wix Editor'ı açın
2. Sol menüden **Dev Mode** → **Turn on Dev Mode**

### Adım 2: iframe Elementi Ekleyin
1. Sayfaya **Embed** → **Custom Element** veya **HTML iframe** ekleyin
2. iframe ID'sini `documanderFrame` olarak ayarlayın

### Adım 3: Sayfa Kodunu Ekleyin
Sayfanın kod bölümüne (Page Code) şu kodu ekleyin:

```javascript
import wixUsers from 'wix-users-frontend';
import wixPaidPlans from 'wix-pricing-plans-frontend';

$w.onReady(async function () {
    const baseUrl = "https://YOUR-PRODUCTION-URL.emergentagent.com";
    
    // Kullanıcı giriş yapmamışsa
    if (!wixUsers.currentUser.loggedIn) {
        $w("#documanderFrame").src = baseUrl;
        return;
    }
    
    const memberId = wixUsers.currentUser.id;
    
    try {
        // Kullanıcının aktif planlarını al
        const orders = await wixPaidPlans.getCurrentMemberOrders();
        
        let plan = "trial";
        let expires = "";
        
        // Aktif plan bul
        const activeOrder = orders.find(order => order.status === "ACTIVE");
        
        if (activeOrder) {
            const planName = activeOrder.planName.toLowerCase();
            
            if (planName.includes("başlangıç") || planName.includes("starter")) {
                plan = "starter";
            } else if (planName.includes("profesyonel") || planName.includes("professional")) {
                plan = "professional";
            } else if (planName.includes("işletme") || planName.includes("business")) {
                plan = "business";
            } else if (planName.includes("kurumsal") || planName.includes("enterprise")) {
                plan = "enterprise";
            } else if (planName.includes("sınırsız") || planName.includes("unlimited")) {
                plan = "unlimited";
            } else if (planName.includes("deneme") || planName.includes("trial")) {
                plan = "trial";
            }
            
            if (activeOrder.endDate) {
                expires = activeOrder.endDate.toISOString();
            }
        }
        
        let iframeUrl = `${baseUrl}?wixMemberId=${memberId}&plan=${plan}`;
        if (expires) {
            iframeUrl += `&expires=${encodeURIComponent(expires)}`;
        }
        
        $w("#documanderFrame").src = iframeUrl;
        
    } catch (error) {
        console.error("Plan bilgisi alınamadı:", error);
        $w("#documanderFrame").src = `${baseUrl}?wixMemberId=${memberId}&plan=trial`;
    }
});
```

---

## 2. YENİ: Çoklu Paket Sistemi için Webhook Entegrasyonu

Wix'te yeni abonelik satın alındığında, Documander'a otomatik bildirim göndermek için:

### Wix Velo Backend Kodu (backend/http-functions.js):

```javascript
import { fetch } from 'wix-fetch';

// Plan eşleştirme
const PLAN_MAPPING = {
    "başlangıç": "starter",
    "starter": "starter",
    "profesyonel": "professional", 
    "professional": "professional",
    "işletme": "business",
    "business": "business",
    "kurumsal": "enterprise",
    "enterprise": "enterprise",
    "sınırsız": "unlimited",
    "unlimited": "unlimited"
};

// Wix Plan Purchase Event Handler
export async function wixPaidPlans_onPlanPurchased(event) {
    const { order } = event;
    const memberId = order.buyer.memberId;
    const planName = order.planName.toLowerCase();
    const orderId = order._id;
    
    // Plan ismini Documander formatına çevir
    let documanderPlan = "trial";
    for (const [key, value] of Object.entries(PLAN_MAPPING)) {
        if (planName.includes(key)) {
            documanderPlan = value;
            break;
        }
    }
    
    // Documander Webhook'una bildir
    try {
        const response = await fetch(
            "https://YOUR-PRODUCTION-URL.emergentagent.com/api/webhook/wix/new-order",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                body: `wix_member_id=${memberId}&plan=${documanderPlan}&wix_order_id=${orderId}&secret_key=imeridis-2025`
            }
        );
        
        const result = await response.json();
        console.log("Documander webhook response:", result);
        
    } catch (error) {
        console.error("Documander webhook failed:", error);
    }
}
```

### Webhook Nasıl Çalışır:
1. Kullanıcı Wix'te yeni paket satın alır
2. Wix otomatik olarak `wixPaidPlans_onPlanPurchased` fonksiyonunu çağırır
3. Bu fonksiyon Documander'a POST isteği gönderir
4. Documander yeni paketi kullanıcının mevcut paketlerine EKLER (üzerine yazmaz)
5. Kullanıcı artık hem eski hem yeni paketin kotasını kullanabilir

---

## 3. Admin Panel Erişimi

Admin paneline erişim için:

**URL:** `https://YOUR-PRODUCTION-URL.emergentagent.com/admin`
**Anahtar:** `imeridis-2025`

### Admin Panel Özellikleri:
- Tüm kullanıcıları listeleme
- Kullanıcı filtreleme (Aktif, Süresi Dolmuş, Kotası Dolmuş)
- Her kullanıcının paketlerini görme
- Excel export
- Manuel paket ekleme

### Manuel Paket Ekleme (API):
```bash
curl -X POST "https://YOUR-PRODUCTION-URL.emergentagent.com/api/admin/add-package" \
  -d "key=imeridis-2025" \
  -d "wix_member_id=KULLANICI_WIX_ID" \
  -d "plan=professional"
```

---

## 4. Çoklu Paket Mantığı

**Senaryo:** Kullanıcı "Başlangıç" paketi kullanırken yeni "Profesyonel" paketi alıyor.

**Sonuç:**
- Başlangıç paketi: 600 kalan kota, 15 Haziran 2026'da bitiyor
- Profesyonel paketi: 2500 kalan kota, 23 Aralık 2026'da bitiyor
- **Toplam Kalan Kota:** 3100 fatura

**Kota Kullanım Sırası:**
1. Önce ESKİ paketin (Başlangıç) kotası kullanılır
2. Eski paket bitince/süresi dolunca YENİ pakete (Profesyonel) geçilir

---

## 5. Plan Kodları

| Wix Plan Adı | Documander Kodu | Kota | Süre |
|--------------|-----------------|------|------|
| Deneme | trial | 20 | 7 gün |
| Başlangıç | starter | 1.000 | 12 ay |
| Profesyonel | professional | 2.500 | 12 ay |
| İşletme | business | 5.000 | 12 ay |
| Kurumsal | enterprise | 10.000 | 12 ay |
| Sınırsız | unlimited | ∞ | 12 ay |

---

## Önemli Notlar

- **Admin Anahtarı:** `imeridis-2025` (değiştirmeniz önerilir)
- **Webhook Anahtarı:** Admin anahtarı ile aynı
- Kullanıcı aynı anda birden fazla pakete sahip olabilir
- Paketler birbirinin yerine geçmez, eklenir
- Kotalar otomatik olarak eski paketten yeniye geçer

Sorularınız için: info@documander.com
