"""
Telegram kanali
---------------
Telegram botu, ayni beyni kullanir.

WhatsApp'tan farki: Telegram'da webhook GEREKMIYOR. Bot, Telegram'a
"yeni mesaj var mi?" diye sorup bekliyor (uzun yoklama). Bu yuzden
ngrok'a, sabit adrese, dogrulamaya ihtiyac yok.

Calismasi icin .env icinde TELEGRAM_TOKEN olmali.
Token'i Telegram'da @BotFather'dan aliyorsun.
"""

import os
import re
import threading
import time

import requests

from beyin import cevapla, sifirla

KONUSMALAR: dict[str, list] = {}
KARAKTER_SINIRI = 3500        # Telegram tek mesajda 4096 karakter kabul ediyor

_ADRES = "https://api.telegram.org/bot{token}/{metod}"


def telegram_bicimi(metin: str) -> str:
    """Claude'un **kalin** yazisini Telegram'in *kalin* bicimine cevirir."""
    metin = re.sub(r"\*\*(.+?)\*\*", r"*\1*", metin)
    if len(metin) > KARAKTER_SINIRI:
        metin = metin[:KARAKTER_SINIRI].rsplit(" ", 1)[0] + "..."
    return metin


def _gonder(token: str, sohbet: int, metin: str) -> None:
    """Mesaji yollar. Bicimlendirme hata verirse duz metin olarak tekrar dener."""
    adres = _ADRES.format(token=token, metod="sendMessage")
    y = requests.post(
        adres,
        json={"chat_id": sohbet, "text": metin, "parse_mode": "Markdown"},
        timeout=20,
    )
    if y.status_code >= 300:
        duz = metin.replace("*", "")
        y = requests.post(adres, json={"chat_id": sohbet, "text": duz}, timeout=20)
        if y.status_code >= 300:
            print(f"  [telegram HATA {y.status_code}] {y.text[:200]}")


def _mesaji_isle(token: str, mesaj: dict) -> None:
    metin = (mesaj.get("text") or "").strip()
    sohbet = mesaj.get("chat", {}).get("id")
    if not metin or sohbet is None:
        return

    kimlik = str(sohbet)
    print(f"  [telegram GELEN] {kimlik}: {metin[:70]}")

    if metin.lower() in ("/start", "start"):
        _gonder(token, sohbet, "Hi! How can I help you today?")
        return

    if metin.lower() in ("/reset", "/yeni", "reset"):
        sifirla(KONUSMALAR, kimlik)
        _gonder(token, sohbet, "Conversation reset. Ask me anything.")
        return

    try:
        cevap = cevapla(KONUSMALAR, kimlik, metin, etiket="telegram")
        _gonder(token, sohbet, telegram_bicimi(cevap))
        print(f"  [telegram] cevap gonderildi -> {kimlik}")
    except Exception as hata:
        print(f"  [telegram HATA] {hata}")
        _gonder(token, sohbet, "Sorry, I can't answer right now. Please try again shortly.")


def _dongu(token: str) -> None:
    """Telegram'a surekli 'yeni mesaj var mi' diye sorar."""
    sonraki = None
    while True:
        try:
            y = requests.get(
                _ADRES.format(token=token, metod="getUpdates"),
                params={"timeout": 30, "offset": sonraki},
                timeout=45,
            )
            for guncelleme in y.json().get("result", []):
                sonraki = guncelleme["update_id"] + 1
                mesaj = guncelleme.get("message") or guncelleme.get("edited_message")
                if mesaj:
                    _mesaji_isle(token, mesaj)
        except requests.exceptions.ReadTimeout:
            continue                      # normal, yeni mesaj gelmedi
        except Exception as hata:
            print(f"  [telegram baglanti hatasi] {hata}")
            time.sleep(3)


def baslat() -> bool:
    """TELEGRAM_TOKEN varsa botu arka planda calistirir."""
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        return False

    try:
        y = requests.get(_ADRES.format(token=token, metod="getMe"), timeout=15).json()
        if not y.get("ok"):
            print(f"  ! Telegram token gecersiz: {y.get('description')}")
            return False
        ad = y["result"].get("username", "?")
    except Exception as hata:
        print(f"  ! Telegram'a baglanilamadi: {hata}")
        return False

    threading.Thread(target=_dongu, args=(token,), daemon=True).start()
    print(f"  Telegram  : baglandi  ->  t.me/{ad}")
    return True
