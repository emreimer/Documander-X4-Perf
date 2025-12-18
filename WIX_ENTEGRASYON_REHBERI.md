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
import wixUsers from 'wix-users';
import wixLocation from 'wix-location';

$w.onReady(function () {
    const baseUrl = "https://finance-assist-28.preview.emergentagent.com";
    
    // Kullanıcı giriş yapmış mı kontrol et
    if (wixUsers.currentUser.loggedIn) {
        // Member ID'yi al
        wixUsers.currentUser.getEmail()
            .then((email) => {
                const memberId = wixUsers.currentUser.id;
                
                // iframe URL'sine member ID ekle
                const iframeUrl = `${baseUrl}?wixMemberId=${memberId}`;
                
                // iframe'i güncelle
                $w("#documanderFrame").src = iframeUrl;
            });
    } else {
        // Giriş yapmamış kullanıcı - normal URL
        $w("#documanderFrame").src = baseUrl;
    }
});
```

### Adım 4: HTML Embed Kullanıyorsanız
Alternatif olarak HTML Embed kullanabilirsiniz:

```html
<div id="documander-container" style="width:100%; height:800px;">
    <iframe 
        id="documanderFrame"
        src="https://finance-assist-28.preview.emergentagent.com"
        style="width:100%; height:100%; border:none;"
        allow="clipboard-write"
    ></iframe>
</div>

<script>
// Wix'ten member ID alınacak - Velo ile entegre edilecek
</script>
```

---

## 2. Abonelik Aktivasyonu (Ödeme Sonrası)

Wix'te ödeme tamamlandığında, aboneliği aktive etmek için:

### Manuel Aktivasyon (Şimdilik)
Wix'ten ödeme bildirimi geldiğinde, bu API'yi çağırın:

```bash
curl -X POST "https://finance-assist-28.preview.emergentagent.com/api/admin/activate-subscription" \
  -d "wix_member_id=KULLANICI_WIX_ID" \
  -d "plan=starter" \
  -d "admin_key=documander-admin-key-2025"
```

### Plan Kodları:
- `starter` → Başlangıç (₺699, 1000 fatura)
- `professional` → Profesyonel (₺1399, 2500 fatura)
- `business` → İşletme (₺2399, 5000 fatura)
- `enterprise` → Kurumsal (₺3999, 10000 fatura)
- `unlimited` → Sınırsız

### Abonelik İptali
```bash
curl -X POST "https://finance-assist-28.preview.emergentagent.com/api/admin/deactivate-subscription" \
  -d "wix_member_id=KULLANICI_WIX_ID" \
  -d "admin_key=documander-admin-key-2025"
```

### Tüm Abonelikleri Listele
```bash
curl "https://finance-assist-28.preview.emergentagent.com/api/admin/subscriptions?admin_key=documander-admin-key-2025"
```

---

## 3. Wix Webhook Entegrasyonu (İleri Seviye)

Wix'te ödeme tamamlandığında otomatik aktivasyon için:

### Wix Velo Backend Kodu (backend/http-functions.js):

```javascript
import { ok, serverError } from 'wix-http-functions';
import wixPaidPlans from 'wix-paid-plans-backend';

// Wix plan ID'leri ile Documander planlarını eşleştir
const PLAN_MAPPING = {
    "wix-plan-id-starter": "starter",
    "wix-plan-id-professional": "professional",
    "wix-plan-id-business": "business",
    "wix-plan-id-enterprise": "enterprise"
};

export async function onPlanPurchased(event) {
    const { memberId, planId } = event;
    const documanderPlan = PLAN_MAPPING[planId];
    
    if (!documanderPlan) return;
    
    // Documander API'sine bildir
    try {
        const response = await fetch(
            "https://finance-assist-28.preview.emergentagent.com/api/admin/activate-subscription",
            {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: `wix_member_id=${memberId}&plan=${documanderPlan}&admin_key=documander-admin-key-2025`
            }
        );
        console.log("Subscription activated:", await response.json());
    } catch (error) {
        console.error("Activation failed:", error);
    }
}
```

---

## 4. Test Etme

1. Wix sitenizde giriş yapın
2. Documander iframe'ini açın
3. Header'da plan ve kota bilgisini kontrol edin
4. Wix Member ID'niz ile abonelik aktive edilmişse, doğru plan görünmeli

---

## Önemli Notlar

- **Admin Key**: `documander-admin-key-2025` (değiştirmeniz önerilir)
- **iframe URL**: `https://finance-assist-28.preview.emergentagent.com`
- **Wix Member ID**: Wix'te her kullanıcının benzersiz ID'si

Sorularınız için: info@documander.com
