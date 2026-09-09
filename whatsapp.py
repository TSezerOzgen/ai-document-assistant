"""
WhatsApp kanali
---------------
Twilio'dan gelen WhatsApp mesajlarini ayni beyne baglar.

Akis:
  Musteri WhatsApp'a yazar
    -> Twilio bu adrese POST atar (/whatsapp)
    -> Claude cevabi uretir
    -> TwiML olarak Twilio'ya doneriz
    -> Twilio musteriye WhatsApp'tan yollar

Onemli: web arayuzuyle AYNI beyni kullanir. Belgeler, kurallar, karakter
hepsi ortak. Yeni kanal = yeni boru, beyin degismiyor.
"""

import html
import re

from fastapi import APIRouter, Form
from fastapi.responses import Response

router = APIRouter()

# telefon numarasi -> konusma gecmisi.  Sunucu kapaninca silinir.
KONUSMALAR: dict[str, list] = {}

GECMIS_SINIRI = 12      # numara basina saklanan mesaj sayisi
KARAKTER_SINIRI = 1500  # Twilio tek mesajda ~1600 karakter kabul ediyor


def whatsapp_bicimi(metin: str) -> str:
    """Markdown kalin yaziyi WhatsApp bicimine cevirir: **soz** -> *soz*"""
    metin = re.sub(r"\*\*(.+?)\*\*", r"*\1*", metin)
    if len(metin) > KARAKTER_SINIRI:
        metin = metin[:KARAKTER_SINIRI].rsplit(" ", 1)[0] + "..."
    return metin


def twiml(mesaj: str) -> Response:
    """Twilio'nun bekledigi XML cevabi uretir."""
    govde = html.escape(mesaj)
    xml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{govde}</Message></Response>'
    return Response(content=xml, media_type="application/xml")


@router.post("/whatsapp")
async def whatsapp_mesaji(Body: str = Form(default=""), From: str = Form(default="")):
    # Dairesel import olmasin diye burada iceri aliyoruz
    from app import ANAHTAR_VAR, MODEL, client, sistem_metni

    soru = (Body or "").strip()
    numara = From or "bilinmeyen"

    if not soru:
        return twiml("Merhaba! Size nasil yardimci olabilirim?")

    if not ANAHTAR_VAR:
        return twiml("Sistem henuz yapilandirilmadi (API anahtari eksik).")

    # sohbeti sifirlama komutu
    if soru.lower() in ("reset", "sifirla", "/reset", "yeni"):
        KONUSMALAR.pop(numara, None)
        return twiml("Konusma sifirlandi. Yeni bir soru sorabilirsiniz.")

    gecmis = KONUSMALAR.setdefault(numara, [])
    gecmis.append({"role": "user", "content": soru})
    del gecmis[:-GECMIS_SINIRI]

    try:
        yanit = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=[{
                "type": "text",
                "text": sistem_metni(),
                "cache_control": {"type": "ephemeral"},
            }],
            messages=gecmis,
        )
        cevap = "".join(p.text for p in yanit.content if p.type == "text").strip()
        gecmis.append({"role": "assistant", "content": cevap})

        k = yanit.usage
        print(f"  [whatsapp] {numara} | giris:{k.input_tokens} cikis:{k.output_tokens}")
        print(f"             soru : {soru[:60]}")
        print(f"             cevap: {cevap[:60]}")

        return twiml(whatsapp_bicimi(cevap))

    except Exception as hata:
        print(f"  [whatsapp HATA] {hata}")
        gecmis.pop()  # basarisiz soruyu gecmiste birakma
        return twiml("Uzgunum, su an cevap veremiyorum. Biraz sonra tekrar deneyin.")


@router.get("/whatsapp")
def whatsapp_kontrol():
    """Tarayicidan acinca calisir mi diye bakmak icin."""
    return {
        "durum": "hazir",
        "aktif_konusma": len(KONUSMALAR),
        "not": "Twilio bu adrese POST atmali, GET degil.",
    }
