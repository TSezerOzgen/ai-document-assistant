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
BOT_ADI = ""                  # baslat() doldurur, ornek: riverside_dental_demo_bot
BOT_ID = 0

_ADRES = "https://api.telegram.org/bot{token}/{metod}"


def telegram_bicimi(metin: str) -> str:
    """Claude'un **kalin** yazisini Telegram'in *kalin* bicimine cevirir."""
    metin = re.sub(r"\*\*(.+?)\*\*", r"*\1*", metin)
    if len(metin) > KARAKTER_SINIRI:
        metin = metin[:KARAKTER_SINIRI].rsplit(" ", 1)[0] + "..."
    return metin


def _gonder(token: str, sohbet: int, metin: str, yanitla: int | None = None) -> None:
    """Mesaji yollar. Bicimlendirme hata verirse duz metin olarak tekrar dener.
    yanitla: grupta hangi mesaja cevap verildigi gorunsun diye o mesajin id'si."""
    adres = _ADRES.format(token=token, metod="sendMessage")
    ek = {"reply_to_message_id": yanitla, "allow_sending_without_reply": True} if yanitla else {}
    y = requests.post(
        adres,
        json={"chat_id": sohbet, "text": metin, "parse_mode": "Markdown", **ek},
        timeout=20,
    )
    if y.status_code >= 300:
        duz = metin.replace("*", "")
        y = requests.post(adres, json={"chat_id": sohbet, "text": duz, **ek}, timeout=20)
        if y.status_code >= 300:
            print(f"  [telegram HATA {y.status_code}] {y.text[:200]}")


def _gruba_mi_soruldu(mesaj: dict, metin: str) -> bool:
    """Grupta bot sadece kendisine seslenilince cevap verir: @etiket, botun mesajina
    yanit ya da komut. Bot yonetici yapilsa bile her mesaja atlamasin diye."""
    if metin.startswith("/"):
        return True
    if BOT_ADI and f"@{BOT_ADI.lower()}" in metin.lower():
        return True
    yanit = mesaj.get("reply_to_message") or {}
    return bool(BOT_ID) and (yanit.get("from") or {}).get("id") == BOT_ID


def _mesaji_isle(token: str, mesaj: dict) -> None:
    metin = (mesaj.get("text") or "").strip()
    sohbet = mesaj.get("chat", {}).get("id")
    if not metin or sohbet is None:
        return

    grup = mesaj.get("chat", {}).get("type") in ("group", "supergroup")
    if grup and not _gruba_mi_soruldu(mesaj, metin):
        return

    # "@botadi" etiketini ve "/start@botadi" gibi komut eklerini temizle
    if BOT_ADI:
        metin = re.sub(rf"@{re.escape(BOT_ADI)}\b", "", metin, flags=re.IGNORECASE).strip()
    if not metin:
        return

    # Grupta her uyenin kendi konusma gecmisi olsun, sorular birbirine karismasin
    kisi = (mesaj.get("from") or {}).get("id")
    kimlik = f"{sohbet}:{kisi}" if grup and kisi else str(sohbet)
    yanitla = mesaj.get("message_id") if grup else None
    print(f"  [telegram GELEN] {kimlik}: {metin[:70]}")

    if metin.lower() in ("/start", "start"):
        _gonder(token, sohbet, "Hi! How can I help you today?", yanitla)
        return

    if metin.lower() in ("/reset", "/yeni", "reset"):
        sifirla(KONUSMALAR, kimlik)
        _gonder(token, sohbet, "Conversation reset. Ask me anything.", yanitla)
        return

    try:
        cevap = cevapla(KONUSMALAR, kimlik, metin, etiket="telegram")
        _gonder(token, sohbet, telegram_bicimi(cevap), yanitla)
        print(f"  [telegram] cevap gonderildi -> {kimlik}")
    except Exception as hata:
        print(f"  [telegram HATA] {hata}")
        _gonder(token, sohbet, "Sorry, I can't answer right now. Please try again shortly.", yanitla)


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
        global BOT_ADI, BOT_ID
        BOT_ADI, BOT_ID = ad, y["result"].get("id", 0)
    except Exception as hata:
        print(f"  ! Telegram'a baglanilamadi: {hata}")
        return False

    threading.Thread(target=_dongu, args=(token,), daemon=True).start()
    print(f"  Telegram  : baglandi  ->  t.me/{ad}")
    return True
