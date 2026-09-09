"""
WhatsApp kanali
---------------
Twilio'dan gelen WhatsApp mesajlarini ayni beyne baglar.

Iki calisma sekli var:

  1) API MODU (onerilen)
     .env icinde TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN varsa,
     cevabi Twilio'nun API'siyle biz gonderiyoruz.
     Twilio'nun yeni "Tryout" arayuzu bunu gerektiriyor.

  2) TwiML MODU (yedek)
     Twilio bilgileri yoksa cevabi XML olarak doneriz.
     Klasik sandbox'ta bu yeterliydi.

Her iki durumda da beyin ayni: belgeler, kurallar, karakter ortak.
"""

import html
import os
import re

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Form
from fastapi.responses import Response

load_dotenv()

router = APIRouter()

KONUSMALAR: dict[str, list] = {}
GECMIS_SINIRI = 12
KARAKTER_SINIRI = 1500

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_NUMARA = os.getenv("TWILIO_WHATSAPP_NUMARA", "+17372508034").strip()
API_MODU = bool(TWILIO_SID and TWILIO_TOKEN)


def whatsapp_bicimi(metin: str) -> str:
    """Markdown kalin yaziyi WhatsApp bicimine cevirir: **soz** -> *soz*"""
    metin = re.sub(r"\*\*(.+?)\*\*", r"*\1*", metin)
    if len(metin) > KARAKTER_SINIRI:
        metin = metin[:KARAKTER_SINIRI].rsplit(" ", 1)[0] + "..."
    return metin


def twiml(mesaj: str = "") -> Response:
    """Twilio'nun bekledigi XML cevabi. Bos mesaj = hicbir sey gonderme."""
    if mesaj:
        govde = f"<Message>{html.escape(mesaj)}</Message>"
    else:
        govde = ""
    xml = f'<?xml version="1.0" encoding="UTF-8"?><Response>{govde}</Response>'
    return Response(content=xml, media_type="text/xml")


def cevap_uret(numara: str, soru: str) -> str:
    """Konusma gecmisini kullanarak Claude'dan cevap alir."""
    from app import MODEL, client, sistem_metni

    gecmis = KONUSMALAR.setdefault(numara, [])
    gecmis.append({"role": "user", "content": soru})
    del gecmis[:-GECMIS_SINIRI]

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
    print(f"             soru : {soru[:70]}")
    print(f"             cevap: {cevap[:70]}")
    return cevap


def twilio_ile_gonder(numara: str, mesaj: str, kimden: str = "") -> None:
    """Cevabi Twilio API uzerinden WhatsApp'a yollar.

    kimden: mesajin geldigi Twilio numarasi. Bos birakilirsa .env'deki
    numara kullanilir. Boylece sandbox degisse bile ayar degistirmen gerekmez.
    """
    adres = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    kimden = kimden or TWILIO_NUMARA
    if not kimden.startswith("whatsapp:"):
        kimden = f"whatsapp:{kimden}"
    try:
        y = requests.post(
            adres,
            auth=(TWILIO_SID, TWILIO_TOKEN),
            data={"From": kimden, "To": numara, "Body": mesaj},
            timeout=20,
        )
        if y.status_code >= 300:
            print(f"  [twilio HATA {y.status_code}] {y.text[:300]}")
        else:
            print(f"  [twilio] cevap gonderildi -> {numara}")
    except Exception as hata:
        print(f"  [twilio HATA] {hata}")


def arka_planda_isle(numara: str, soru: str, kimden: str = "") -> None:
    """Cevabi uretip Twilio API ile yollar (webhook zaman asimina ugramasin diye)."""
    try:
        cevap = cevap_uret(numara, soru)
        twilio_ile_gonder(numara, whatsapp_bicimi(cevap), kimden)
    except Exception as hata:
        print(f"  [whatsapp HATA] {hata}")
        KONUSMALAR.get(numara, []) and KONUSMALAR[numara].pop()
        twilio_ile_gonder(numara, "Sorry, I can't answer right now. Please try again shortly.", kimden)


@router.post("/whatsapp")
async def whatsapp_mesaji(
    arka: BackgroundTasks,
    Body: str = Form(default=""),
    From: str = Form(default=""),
    To: str = Form(default=""),
):
    from app import ANAHTAR_VAR

    soru = (Body or "").strip()
    numara = From or "bilinmeyen"
    print(f"  [whatsapp GELEN] {numara}: {soru[:70]}")

    if not soru:
        return twiml("Hi! How can I help you today?")

    if not ANAHTAR_VAR:
        return twiml("The assistant is not configured yet (missing API key).")

    if soru.lower() in ("reset", "sifirla", "/reset", "new"):
        KONUSMALAR.pop(numara, None)
        return twiml("Conversation reset. Ask me anything.")

    if API_MODU:
        # Cevabi arka planda uret ve Twilio API ile yolla.
        # Webhook'a hemen bos cevap donuyoruz ki Twilio beklemesin.
        arka.add_task(arka_planda_isle, numara, soru, To)
        return twiml()

    # Yedek yol: Twilio bilgileri yoksa cevabi XML olarak don
    try:
        return twiml(whatsapp_bicimi(cevap_uret(numara, soru)))
    except Exception as hata:
        print(f"  [whatsapp HATA] {hata}")
        return twiml("Sorry, I can't answer right now. Please try again shortly.")


@router.get("/whatsapp")
def whatsapp_kontrol():
    return {
        "durum": "hazir",
        "mod": "Twilio API" if API_MODU else "TwiML (yedek)",
        "twilio_numara": TWILIO_NUMARA,
        "aktif_konusma": len(KONUSMALAR),
        "not": "Twilio bu adrese POST atmali, GET degil.",
    }
