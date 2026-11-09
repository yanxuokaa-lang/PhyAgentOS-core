# jev2048

TypeSafe'in **Jev** karar modeli, gerçek bir online 2048 sitesinde oynuyor — hamle başına tek API çağrısıyla.

![Jev 2048 oynuyor](docs/demo.gif)

> Solda ajanın gördüğü: her hamlede dört yönün kalibre olasılığı ve modelin güveni.
> Sağda gerçek site. Kayıt gerçek zamanlı, `--delay 0.5` ile yavaşlatılmış.

## Ne yapıyor

Jev bir dil modeli değil. [System One](https://docs.typesafe.ai/models) sınıfı bir **karar modeli**: ona
durumu ve seçenekleri verirsin, sana kalibre olasılıklarla birlikte seçeneklerden birini döndürür.
Seçenek uzayının dışına çıkamaz, yani bu bağlamda halüsinasyon yapması mümkün değil.

Bu proje o fikri en saf hâliyle gösteriyor. 2048'de karar uzayı sabit ve dört tane:

```
tahta okunur  →  Jev'e 4 seçenek sunulur  →  seçilen yön klavyeden basılır  →  tekrar
```

Her turda tek soru, tek HTTP isteği, tek hamle. Terminalde dört yönün olasılığını da görürsün:

```
   .    2    .    4
   .    8    .    .
   2    .    .    .
   .    .    4   16

#7  skor 48  →  LEFT
  UP    ███·················  14.2%
  DOWN  ██·················    9.1%
  LEFT  ██████████████······  68.4%  ◀
  RIGHT ██··················   8.3%
  güven 68.4%   41 ms
```

### Neden tek API anahtarı

Bu ajan hiç metin üretmiyor — sadece seçim yapıyor. Genel amaçlı tarayıcı ajanlarının form
doldurmak için ihtiyaç duyduğu ikinci bir dil modeli burada gerekmiyor. Tek anahtarla çalışır.

## Kurulum

```bash
git clone <bu-repo>
cd 2048
uv sync
uv run playwright install chromium
cp .env.example .env    # TYPESAFE_API_KEY değerini gir
uv run jev2048
```

`uv` kurulu değilse:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Anahtarını [console.typesafe.ai](https://console.typesafe.ai) adresinden alıyorsun.
`.env` dosyası `.gitignore`'da — anahtarın repoya karışmaz.

## Bayraklar

| Bayrak | Anlamı | Varsayılan |
| --- | --- | --- |
| `--url` | Oynanacak 2048 sitesi | `https://2048.io/` |
| `--max-moves` | Hamle limiti | 500 |
| `--stuck-limit` | Arka arkaya kaç etkisiz hamlede durulacağı | 6 |
| `--delay` | Hamleler arası ek bekleme (sn); izlerken yavaşlatmak için | 0 |
| `--headless` | Tarayıcıyı gizle | kapalı |
| `--json` | İnsan çıktısı yerine satır başına bir JSON kaydı bas | kapalı |

```bash
uv run jev2048 --max-moves 50 --delay 0.3     # yavaş, izlemek için
uv run jev2048 --headless --json > oyun.jsonl # veri toplamak için
```

## Nasıl çalışıyor

| Modül | Sorumluluk |
| --- | --- |
| `board.py` | Saf veri. Tarayıcı, ağ, ortam değişkeni bilmez. Tüm ayrıştırma ve doğrulama burada. |
| `model.py` | TypeSafe istemcisi. İstek kurar, yanıtı doğrular, `Decision` döndürür. |
| `browser.py` | Playwright sarmalayıcı. Tahtayı okur, tuşa basar. |
| `agent.py` | Oku → sor → bas döngüsü. |
| `cli.py` | Sadece sunum. |

Karar mantığı ve ayrıştırma saf fonksiyonlarda olduğu için testler ne tarayıcı açar ne ağa çıkar.

### Tahta nasıl okunuyor

Naif yaklaşım — tuşa bas, biraz bekle, DOM'u oku — **bayat tahta** döndürür. 2048'in kaynak kodunda
`actuate()` şunu yapıyor:

1. `localStorage.gameState` **senkron** yazılır,
2. DOM render'ı `requestAnimationFrame` içine ertelenir,
3. her taş **önce eski pozisyonunda** çizilir, bir sonraki karede yenisine taşınır.

Yani tuşa bastıktan hemen sonra `gameState` doğru, DOM ise geride. Bu yüzden sabit bir `sleep`
yerine **DOM ile `gameState` eşleşene kadar** bekleniyor — gerçek bir bitiş sinyali, hem hızlı hem
güvenilir. Oyun bittiğinde site `gameState`i sildiği için o durumda tek kaynak DOM oluyor.

### Modelin kararına karışılmıyor

Dört yön modele **her zaman** sunuluyor. "Bu yön tahtayı değiştirmiyor" diye seçenek elenmiyor,
heuristik skor ipucu da verilmiyor — karar tamamen Jev'in. Tek istisna bilgilendirme: tahtayı
değiştirmeyen bir hamle `recent_moves` içine `changed: false` olarak yazılıp bir sonraki tura
state olarak dönüyor, böylece model aynı geçersiz yönde sonsuz döngüye girmiyor.

## Sınırlar — dürüstçe

**Bu bir 2048 çözücüsü değil.** Jev tek hamlelik karar veriyor; arama, lookahead, expectimax yok.
Skor, arama tabanlı 2048 botlarının belirgin altında kalır. Projenin gösterdiği şey yüksek skor
değil: *bir karar modeli, gerçek bir sitede, hamle başına tek çağrıyla, milisaniyeler içinde oynuyor.*

Ölçülmüş tam bir oyun (`jev-1.13.0`, 2026-09-18):

| | |
| --- | --- |
| Hamle | 127 (oyun sonuna kadar) |
| Skor | 884 |
| En yüksek taş | 64 |
| Hız | 2,57 hamle/sn — hamle başına ~300 ms |
| Maliyet | 140.467 girdi token ≈ **$0,006** |

Karşılaştırma için: expectimax tabanlı botlar rutin olarak 2048 ve 4096 taşına ulaşır.

### Bir entegrasyon detayı: argmax varsayımı

Jev, `probabilities` değerlerini **2 ondalık basamağa yuvarlayarak** raporluyor. Neredeyse
berabere dağılımlarda (2048'de sık) döndürülen `choice`, raporlanan argmax'tan **bir yuvarlama
birimi** sapabiliyor. Ölçtük: 40 istekte 3 sapma, **hepsi tam 0,01**, daha büyüğü yok.

`choice == argmax(probabilities)` varsayımıyla sıkı doğrulama yaparsan bu yanıtları bozuk sanıp
ajanı durdurursun — bizde ilk denemede 77. hamlede oldu. `validate_choice` bu yüzden
`ARGMAX_TOLERANCE = 0.02` kullanıyor: rapor gürültüsünü kapsıyor ama gerçek tutarsızlığı
(0,60'a karşı 0,05) hâlâ reddediyor.

## Site uyumluluğu

Klasik **DOM tabanlı** 2048 gerekiyor. Varsayılan `2048.io`; gerçek tarayıcıda test edilmiş
alternatifler:

```bash
uv run jev2048 --url https://www.2048.org/
uv run jev2048 --url https://2048game.com/
```

Çalışmayanlar:

- **`play2048.co`** — PixiJS/WebGL canvas'a taşınmış, sayfada okunabilir tahta yok. Jev metin
  girdisi aldığı için ekran görüntüsü göndermek de seçenek değil.
- **`gabrielecirulli.github.io/2048/`** — tarayıcıda JavaScript ile `play2048.co`'ya yönlendiriyor.
  (`curl` ile bakarsan klasik HTML görürsün; JS çalışmadığı için yanıltıcı.)

## Geliştirme

```bash
uv run pytest          # 52 test, ağ ve tarayıcı gerektirmez
uv run ruff check .
uv run python scripts/smoke.py   # gerçek anahtarla gerçek siteye karşı
```

## Tasarım notları

Bu proje tasarım-önce yazıldı ve yol boyunca çıkan sürprizler belgelendi:

- [`docs/design.md`](docs/design.md) — mimari, site sözleşmesi, hata durumları ve
  implementasyon sırasında ortaya çıkan iki düzeltme (hedef site değişikliği, argmax toleransı)
- [`docs/plan.md`](docs/plan.md) — göreve bölünmüş TDD planı

## Atıf

- [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) (MIT) — `post_json` ve
  `validate_choice` oradan uyarlandı. Genel amaçlı tarayıcı otomasyonu için Jev'i kullanan referans proje.
- 2048: [Gabriele Cirulli](https://github.com/gabrielecirulli/2048) (MIT).

## Lisans

MIT
