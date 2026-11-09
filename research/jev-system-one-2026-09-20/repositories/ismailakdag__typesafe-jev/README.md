# İlan Eleme — sahibinden ilanları için yapay zekâ destekli ön eleme

Gezdiğin ilanı tek tıkla yapılandırılmış veriye çevirir, **TypeSafe (Jev)** ile
değerlendirir ve *favoriye değer / emin değil / değmez* der. Kararı nasıl verdiğini
adım adım izleyebilirsin.

Her şey kendi bilgisayarında çalışır. Tek istisna: değerlendirme sırasında ilan
metni TypeSafe API'sine gider.

```
[1] YAKALA     Chrome eklentisi  →  sayfadaki her alan, konum, açıklama, foto
[2] YARGILA    Jev               →  22 soru, tek çağrı, paralel
[3] KARAR VER  kod               →  kesin filtreler + kırmızı bayraklar + ağırlıklı skor
```

Emlak ve vasıta için ayrı soru setleri var; kategori sayfadan otomatik anlaşılır.

---

## Kurulum

### 1. uv kur

Python'u da kendisi indirir, ayrıca Python kurmana gerek yok.

```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

Bittiğinde **PowerShell penceresini kapat, yenisini aç** — kurulum PATH'e ekliyor
ama açık pencereler bunu görmez. Kontrol: `uv --version`

### 2. Depoyu al

```bash
git clone https://github.com/ismailakdag/typesafe-jev.git
cd typesafe-jev
```

### 3. Sunucuyu başlat

`basla.cmd` dosyasına çift tıkla, ya da:

```bash
uv run python -m server.app
```

İlk açılışta bağımlılıklar iner. Sonra `http://127.0.0.1:8765`.

### 4. Chrome eklentisini yükle

`chrome://extensions` → **Geliştirici modu** → **Paketlenmemiş öğe yükle** →
depodaki `extension` klasörünü seç.

### 5. API anahtarını gir

https://console.typesafe.ai/keys adresinden anahtar al, panelde
**Ayarlar** → yapıştır → **Kaydet** → **Doğrula**.

Anahtar yerel `.env` dosyasına yazılır, depoya girmez.

Ayrıntılı anlatım ve sorun giderme: **[KURULUM.md](KURULUM.md)**

---

## Kullanım

| | |
|---|---|
| **Anlık karar** | İlan sayfasındaki panelden *Değerlendir*. Sonuç + süre + token + maliyet. |
| **Karar akışı** | *Nasıl karar verdi?* — sorular eş zamanlı dolar, kod kapıları sırayla açılır, skor terim terim birikir. Hız: 1x / 2x / 5x / 10x. |
| **Arşive kaydet** | Aynı ilan tekrar kaydedilirse üzerine yazılmaz, yeni sürüm eklenir — fiyat geçmişi. |
| **Toplu eleme** | Panelde kesin sınırlar + profil → *Elemeyi çalıştır*. Kod filtresi anlık ve bedava; kalanlar Jev'e gider. |
| **Kendi soruların** | Panelde *Sorular*. Evet/hayır, dereceli veya seçenekli. Yerleşikler değişmez. |
| **Arşiv yönetimi** | Eklenti popup'ından ara, detay aç, ilana git, sil. |

---

## İş bölümü

Bu ayrım projenin özü:

**Kodda kalanlar** — fiyat, m², km, model yılı, aidat, mesafe, harita alanı.
Hepsi kesin ve sayısal. Jev sayılarda zayıf; üstelik bu filtreler zaten kesin,
modele sormak hem yanlış hem gereksiz maliyet.

**Jev'e sorulanlar** — yalnızca metinden çıkan yargılar: çelişki, abartı, satıcı
dili, teslim durumu, profile uygunluk. Bunları kod yapamaz.

**Kararı yine kod verir** — kırmızı bayraklar ayrı koşuldur, ağırlıklı skora
karışmaz. Ciddi bir kusur, yüksek bakım puanıyla telafi edilemez.

Örnek: bir araba ilanının başlığı *"hasar kaydı yok"* diyebilir. Gövde şemasındaki
boyalı/değişen paneller sayfadan **yapısal olarak** okunur ve modele açıkça
"ikisini karşılaştır" diye sorulur — metinden tahmin etmesi beklenmez.

---

## Ölçülen maliyet

Bir ilan, 22 soru, tek çağrı:

| | 8 soru | 22 soru |
|---|---|---|
| süre | ~750 ms | ~900 ms |
| girdi tokeni | 2.171 | 3.548 |
| maliyet | $0.000091 | $0.000149 |
| 1000 ilan | $0.09 | **$0.15** |

Dağılım: ilan metni + alanlar + profil ~**1.380 token**, her soru kendi
`instructions` ve `criteria` metniyle ~**100 token**. 22 soruda maliyetin ~%60'ı
soruların kendi metni — soru eklemek bedava değil, ucuz.

Değişmeyen şey gecikme: 22 soru için 22 değil **tek istek** gider.

Gerçek sayılar `data/kullanim.json` defterinde birikir.

---

## Kapsam ve sınırlar

- **Kazıma yapmaz.** Eklenti gezmez, sayfa açmaz, arka planda istek atmaz.
  Yalnızca sen bakarken, sen tıklayınca, o anki sayfayı okur. Otomatik
  değerlendirme seçeneği kapalı gelir. Kişisel kullanım için tasarlandı.
- **Veri yerelde kalır.** Sunucu `127.0.0.1`'e bağlanır. Yakalanan ilanlar
  `data/` altında durur ve depoya girmez.
- **Jev metin üretmez.** Tipli yargı ve olasılık döner; ilan metnindeki talimat
  görünümlü ifadeler bu yüzden işlemez.
- **Türkçe** Jev'in birincil eğitim dili değil. Kendi içeriğinde test et ve
  `confidence` değerlerine bak.
- Yargılar karar desteğidir, karar değil. Mesaj atmak, teklif vermek, kapora
  ödemek gibi geri dönüşü olmayan adımlar insanda kalmalı.

---

## Geliştirme

```bash
# Kaydedilmiş bir sayfa üzerinde çıkarımı siteye dokunmadan test et
node tools/test_extract.mjs data/ornek/sayfa.html "https://..."

# Aynı sayfayı Jev'e gönder ve kararı yazdır
node tools/test_extract.mjs data/ornek/sayfa.html "https://..." --degerlendir

# Paylaşılabilir zip üret (.env ve kişisel veri hariç)
uv run python tools/paketle.py
```

Çıkarım CSS sınıf adlarına değil sayfanın **şekline** dayanır (etiket/değer
çiftleri, JSON-LD, meta), konum için dört strateji Türkiye sınırlarıyla
doğrulanır ve ham sayfa metni her zaman saklanır — yapılandırma bir alanı
kaçırsa da veri kaybolmaz.

## Lisans

MIT
