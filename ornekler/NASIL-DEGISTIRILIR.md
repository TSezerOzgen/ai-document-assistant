# Asistanı başka bir işletmeye uyarlama

Kod hiç değişmiyor. Sadece 2 şey yapıyorsun.

## Şu an kurulu olan

`belgeler/clinic-info.txt` — **Riverside Dental Care**, Austin/Teksas.
İngilizce, dolar fiyatlı, ABD sigorta bilgili. Yurt dışı müşterisi için
hazır demo.

## Elindeki diğer örnekler

| Dosya | Ne |
|---|---|
| `turkce-dis-klinigi.txt` | Türkçe diş kliniği (Türk müşteri için) |
| `restoran-bilgileri.txt` | Türkçe restoran (menü, rezervasyon, alerjen) |

## Nasıl değiştirilir

**1.** Eski belgeyi çıkar, yenisini koy:

```bash
mv belgeler/clinic-info.txt ornekler/
mv ornekler/restoran-bilgileri.txt belgeler/
```

**2.** `app.py` içinde 3 satırı değiştir:

```python
ISLETME_ADI    = "Meze & Co."
KARAKTER       = "sıcakkanlı, samimi bir restoran görevlisi"
VARSAYILAN_DIL = "Turkish"
```

**3.** Yeniden çalıştır:

```bash
python app.py
```

Bu kadar.

---

## İşin özü

Her yeni müşteride sıfırdan yazılım yazmıyorsun. O işletmenin bilgilerini
bir metin dosyasına döküp bağlıyorsun.

İlk müşteride 3 gün sürer. Onuncuda 2 saat sürer. Otuzuncuda artık
müşterinin kendi kendine yapabileceği bir sayfa yazarsın — ürün o zaman
doğar.
