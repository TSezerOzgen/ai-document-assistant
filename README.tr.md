# AI Doküman Asistanı

İşletme belgelerini okuyup müşteri sorularını 7/24 cevaplayan asistan.

Bir işletmenin fiyat listesi, çalışma saatleri, hizmetleri ve SSS'i
`belgeler/` klasörüne konur. Asistan sadece o belgelere dayanarak cevap
verir — bilmediği bir şeyi uydurmaz, yetkiliye yönlendirir.

## Ne işe yarıyor

Küçük işletmeler mesai dışı gelen sorulara cevap veremediği için müşteri
kaybediyor. Bu asistan aynı soruları gece 3'te de cevaplıyor.

| Sektör | Kullanım |
|---|---|
| Diş kliniği / doktor | Randevu, fiyat, saat soruları |
| Restoran | Menü, rezervasyon, alerjen bilgisi |
| Emlak | İlan filtreleme, ön eleme |
| E-ticaret | Kargo durumu, iade, beden |
| Otel | Rezervasyon, olanaklar, çok dilli |

## Kurulum

```bash
pip install -r requirements.txt
cp .env.ornek .env      # sonra .env içine API anahtarını yapıştır
python app.py
```

Tarayıcıda `http://127.0.0.1:8000` adresini aç.

## Başka bir işletmeye uyarlama

1. `belgeler/` klasörünü boşalt, o işletmenin dosyalarını koy (.txt .md .pdf)
2. `app.py` içindeki `ISLETME_ADI` ve `KARAKTER` satırlarını değiştir
3. Yeniden çalıştır

Kod değişmiyor — sadece belge ve iki satır ayar.

## Teknik

- **Backend:** Python, FastAPI, streaming yanıt (SSE benzeri NDJSON)
- **Model:** Anthropic Claude (`app.py` içinden değiştirilebilir)
- **Prompt caching:** Belgeler sabit olduğu için önbelleğe alınır,
  yeterince büyük belgelerde giriş maliyeti ~%90 düşer
- **Maliyet takibi:** Her soru sonrası token ve kuruş cinsinden maliyet gösterilir

## Maliyet

Claude Haiku 4.5 ile, ~750 tokenlık bir belge setinde soru başına
yaklaşık **0,008 TL**. 5 dolarlık kredi ≈ **2.800 soru**.
