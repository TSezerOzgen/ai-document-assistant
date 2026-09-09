"""
WhatsApp - Meta Cloud API
-------------------------
WhatsApp'a DOGRUDAN baglanir. Twilio gibi bir araci yok.

Meta'nin verdigi test numarasi ucretsiz ve 5 numaraya kadar serbest
metin gonderebiliyor. Musteri once yazdiginda 24 saat boyunca sablon
zorunlulugu yok - bizim kullanimimiz tam olarak bu.

.env icinde olmasi gerekenler:
    META_TOKEN         Meta panelindeki gecici/kalici erisim anahtari
    META_PHONE_ID      Test numarasinin kimlik numarasi
    META_VERIFY_TOKEN  Webhook dogrulamasi icin kendi belirledigin sifre
"""

import os
import re

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from beyin import cevapla, sifirla

load_dotenv()

router = APIRouter()

KONUSMALAR: dict[str, list] = {}
KARAKTER_SINIRI = 3500

META_TOKEN = os.getenv("META_TOKEN", "").strip()
META_PHONE_ID = os.getenv("META_PHONE_ID", "").strip()
META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "asistan123").strip()
HAZIR = bool(META_TOKEN and META_PHONE_ID)


def whatsapp_bicimi(metin: str) -> str:
    """Claude'un **kalin** yazisini WhatsApp'in *kalin* bicimine cevirir."""
    metin = re.sub(r"\*\*(.+?)\*\*", r"*\1*", metin)
    if len(metin) > KARAKTER_SINIRI:
        metin = metin[:KARAKTER_SINIRI].rsplit(" ", 1)[0] + "..."
    return metin


def _gonder(numara: str, metin: str) -> None:
    adres = f"https://graph.facebook.com/v21.0/{META_PHONE_ID}/messages"
    try:
        y = requests.post(
            adres,
            headers={"Authorization": f"Bearer {META_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": numara,
                "type": "text",
                "text": {"body": metin},
            },
            timeout=20,
        )
        if y.status_code >= 300:
            print(f"  [meta HATA {y.status_code}] {y.text[:300]}")
        else:
            print(f"  [meta] cevap gonderildi -> {numara}")
    except Exception as hata:
        print(f"  [meta HATA] {hata}")


def _isle(numara: str, soru: str) -> None:
    if soru.lower() in ("reset", "/reset", "new", "yeni"):
        sifirla(KONUSMALAR, numara)
        _gonder(numara, "Conversation reset. Ask me anything.")
        return
    try:
        cevap = cevapla(KONUSMALAR, numara, soru, etiket="meta-wa")
        _gonder(numara, whatsapp_bicimi(cevap))
    except Exception as hata:
        print(f"  [meta HATA] {hata}")
        _gonder(numara, "Sorry, I can't answer right now. Please try again shortly.")


@router.get("/meta-whatsapp")
async def dogrula(request: Request):
    """Meta, webhook'u kaydederken bu adrese GET atip dogrulama yapar."""
    p = request.query_params
    if p.get("hub.mode") == "subscribe" and p.get("hub.verify_token") == META_VERIFY_TOKEN:
        print("  [meta] webhook dogrulandi")
        return PlainTextResponse(p.get("hub.challenge", ""))
    print(f"  [meta] webhook dogrulama BASARISIZ (beklenen: {META_VERIFY_TOKEN})")
    return PlainTextResponse("dogrulama basarisiz", status_code=403)


@router.post("/meta-whatsapp")
async def gelen_mesaj(request: Request, arka: BackgroundTasks):
    """Musteriden gelen WhatsApp mesaji."""
    veri = await request.json()
    try:
        for giris in veri.get("entry", []):
            for degisim in giris.get("changes", []):
                deger = degisim.get("value", {})
                for mesaj in deger.get("messages", []):
                    if mesaj.get("type") != "text":
                        _gonder(mesaj["from"], "I can only read text messages right now.")
                        continue
                    numara = mesaj["from"]
                    soru = mesaj["text"]["body"].strip()
                    print(f"  [meta GELEN] {numara}: {soru[:70]}")
                    if soru and HAZIR:
                        arka.add_task(_isle, numara, soru)
    except Exception as hata:
        print(f"  [meta ayristirma hatasi] {hata}")

    # Meta 200 bekliyor, yoksa mesaji tekrar tekrar gonderiyor
    return JSONResponse({"durum": "alindi"})


@router.get("/meta-durum")
def durum():
    return {
        "hazir": HAZIR,
        "phone_id": META_PHONE_ID or "(yok)",
        "token": "VAR" if META_TOKEN else "YOK",
        "verify_token": META_VERIFY_TOKEN,
        "aktif_konusma": len(KONUSMALAR),
    }
