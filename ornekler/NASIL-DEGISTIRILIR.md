# Asistanı başka bir işletmeye uyarlama

Kod hiç değişmiyor. Sadece 2 şey yapıyorsun:

## 1. Belgeyi değiştir

```bash
# eski işletmenin belgesini çıkar
mv belgeler/klinik-bilgileri.txt ornekler/

# yeni işletmenin belgesini koy
mv ornekler/restoran-bilgileri.txt belgeler/
```

## 2. app.py içinde 2 satırı değiştir

```python
ISLETME_ADI = "Meze & Co."
KARAKTER = "sıcakkanlı, samimi bir restoran görevlisi"
```

## 3. Yeniden çalıştır

```bash
python app.py
```

Bu kadar. Aynı kod, farklı işletme.

**İşin özü bu:** Her yeni müşteride sıfırdan yazılım yazmıyorsun.
Sadece o işletmenin bilgilerini bir metin dosyasına döküp bağlıyorsun.
İlk müşteride 3 gün sürer, onuncu müşteride 2 saat sürer.
