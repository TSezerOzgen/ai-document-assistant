"""
AI Dokuman Asistani
-------------------
belgeler/ klasorundeki dosyalari okur ve gelen sorulari
SADECE o belgelere dayanarak cevaplar.

Calistirmak icin:  python app.py
"""

import json
import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

load_dotenv()

# =====================================================================
#  AYARLAR  -  burayi degistirerek asistani her isletmeye uyarlarsin
# =====================================================================

ISLETME_ADI = "Riverside Dental Care"

KARAKTER = "a warm, concise front-desk receptionist"

# Musterinin yazdigi dilde cevap verir; hangi dili varsayacagini burasi belirler
VARSAYILAN_DIL = "English"

MODEL = "claude-haiku-4-5"
# Daha akilli (ve pahali) secenekler - satiri degistirmen yeterli:
#   MODEL = "claude-sonnet-5"   ->  ~2 kat maliyet
#   MODEL = "claude-opus-5"     ->  ~5 kat maliyet

# 1 milyon token basina USD (maliyet gostergesi icin)
FIYATLAR = {
    "claude-haiku-4-5": {"giris": 1.00, "cikis": 5.00},
    "claude-sonnet-5":  {"giris": 2.00, "cikis": 10.00},
    "claude-opus-5":    {"giris": 5.00, "cikis": 25.00},
}

# =====================================================================


KOK = Path(__file__).parent
BELGE_KLASORU = KOK / "belgeler"


def belgeleri_oku() -> str:
    """belgeler/ icindeki tum .txt .md .pdf dosyalarini tek metne cevirir."""
    parcalar = []

    for dosya in sorted(BELGE_KLASORU.iterdir()):
        if dosya.name.startswith("."):
            continue

        metin = ""
        if dosya.suffix.lower() in (".txt", ".md"):
            metin = dosya.read_text(encoding="utf-8", errors="ignore")

        elif dosya.suffix.lower() == ".pdf":
            try:
                from pypdf import PdfReader
                metin = "\n".join(s.extract_text() or "" for s in PdfReader(dosya).pages)
            except Exception as hata:
                print(f"  ! {dosya.name} okunamadi: {hata}")
                continue
        else:
            continue

        if metin.strip():
            parcalar.append(f"--- DOSYA: {dosya.name} ---\n{metin.strip()}")

    return "\n\n".join(parcalar)


def sistem_metni() -> str:
    belgeler = belgeleri_oku()
    return f"""You are the customer assistant for {ISLETME_ADI}.
Your persona: {KARAKTER}.

Below is the official information for this business. Answer customer
questions using ONLY this information.

RULES:
1. If the answer is not in the information, do not invent one. Say you
   don't have that detail and offer to connect them with a team member.
   Then share whatever related information you DO have.
2. Be brief. Two or three short sentences. No long explanations and no
   bullet lists unless the customer asks for details.
3. Reply in the same language the customer writes in.
   Default to {VARSAYILAN_DIL}.
4. Quote prices, hours and addresses exactly as written below.
5. Highlight key facts like prices and hours with **double asterisks**.
6. Sound like a helpful person, not a robot. Warm, never pushy.

===== BUSINESS INFORMATION =====
{belgeler}
===== END OF INFORMATION ====="""


anahtar = os.getenv("ANTHROPIC_API_KEY", "").strip()
ANAHTAR_VAR = anahtar.startswith("sk-ant-")

# Anahtar yoksa sunucu yine de acilir (ONIZLEME MODU): arayuzu gorebilir,
# tiklayabilirsin. Anahtari .env'e ekleyip yeniden baslatinca gercek cevap verir.
client = Anthropic(api_key=anahtar) if ANAHTAR_VAR else None
app = FastAPI(title="AI Dokuman Asistani")

# WhatsApp kanalini bagla - ayni beyni kullanir, sadece yeni bir giris kapisi
from whatsapp import router as whatsapp_router
app.include_router(whatsapp_router)


class Istek(BaseModel):
    mesajlar: list


@app.get("/")
def anasayfa():
    return FileResponse(KOK / "static" / "index.html")


@app.get("/bilgi")
def bilgi():
    belgeler = belgeleri_oku()
    return {
        "isletme": ISLETME_ADI,
        "model": MODEL,
        "belge_sayisi": len([d for d in BELGE_KLASORU.iterdir() if not d.name.startswith(".")]),
        "karakter_sayisi": len(belgeler),
    }


@app.post("/sor")
def sor(istek: Istek):
    def uret():
        if not ANAHTAR_VAR:
            mesaj = ("[ONIZLEME MODU] Arayuz calisiyor, ama henuz API anahtarin yok, "
                     "bu yuzden gercek cevap uretemiyorum. "
                     "Anahtari .env dosyasina ekleyip 'python app.py' komutunu tekrar "
                     "calistirdiginda burasi gercek cevaplar vermeye baslayacak.")
            for kelime in mesaj.split(" "):
                yield json.dumps({"tip": "metin", "veri": kelime + " "}, ensure_ascii=False) + "\n"
            yield json.dumps({"tip": "maliyet", "usd": 0, "kurus": 0,
                              "giris": 0, "cikis": 0, "onbellek_okundu": 0},
                             ensure_ascii=False) + "\n"
            return

        toplam = ""
        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=500,
                system=[{
                    "type": "text",
                    "text": sistem_metni(),
                    # Belgeler her soruda ayni -> onbellege alinir, %90 ucuzlar
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=istek.mesajlar,
            ) as akis:
                for parca in akis.text_stream:
                    toplam += parca
                    yield json.dumps({"tip": "metin", "veri": parca}, ensure_ascii=False) + "\n"
                son = akis.get_final_message()

            k = son.usage
            giris     = getattr(k, "input_tokens", 0) or 0
            cikis     = getattr(k, "output_tokens", 0) or 0
            cache_yaz = getattr(k, "cache_creation_input_tokens", 0) or 0
            cache_oku = getattr(k, "cache_read_input_tokens", 0) or 0

            f = FIYATLAR.get(MODEL, FIYATLAR["claude-haiku-4-5"])
            usd = (
                giris * f["giris"]
                + cache_yaz * f["giris"] * 1.25   # onbellege yazma
                + cache_oku * f["giris"] * 0.10   # onbellekten okuma (10x ucuz)
                + cikis * f["cikis"]
            ) / 1_000_000

            print(f"  soru islendi | giris:{giris} onbellek:{cache_oku} cikis:{cikis} | ${usd:.6f}")

            yield json.dumps({
                "tip": "maliyet",
                "usd": round(usd, 6),
                "kurus": round(usd * 48.46 * 100, 2),
                "giris": giris, "cikis": cikis,
                "onbellek_okundu": cache_oku,
            }, ensure_ascii=False) + "\n"

        except Exception as hata:
            yield json.dumps({"tip": "hata", "veri": str(hata)}, ensure_ascii=False) + "\n"

    return StreamingResponse(uret(), media_type="application/x-ndjson")


if __name__ == "__main__":
    import uvicorn

    belgeler = belgeleri_oku()
    print("\n" + "=" * 58)
    print(f"  {ISLETME_ADI} - AI Asistan")
    print("=" * 58)
    print(f"  Model     : {MODEL}")
    print(f"  API       : {'baglandi' if ANAHTAR_VAR else 'ONIZLEME MODU - anahtar yok'}")
    print(f"  Belgeler  : {len(belgeler):,} karakter yuklendi")
    if not belgeler.strip():
        print("  ! UYARI: belgeler/ klasoru bos. Icine .txt veya .pdf koy.")
    print("=" * 58)
    print("\n  Tarayicida ac:  http://127.0.0.1:8000")
    print("  Durdurmak icin: Ctrl + C\n")

    # ---- ngrok tuneli (istege bagli) --------------------------------
    # .env icinde NGROK_TOKEN varsa bilgisayarini internete acar, boylece
    # Twilio WhatsApp mesajlarini buraya iletebilir. Yoksa sadece yerelde calisir.
    ngrok_token = os.getenv("NGROK_TOKEN", "").strip()
    if ngrok_token:
        try:
            from pyngrok import conf, ngrok
            conf.get_default().auth_token = ngrok_token
            adres = ngrok.connect(8000, "http").public_url.replace("http://", "https://")
            print("  TUNEL ACILDI")
            print(f"  Genel adres : {adres}")
            print()
            print("  >>> Twilio WhatsApp Sandbox ayarlarina SU ADRESI yapistir:")
            print(f"      {adres}/whatsapp")
            print("      (WHEN A MESSAGE COMES IN alanina, metodu POST birak)")
            print("=" * 58)
            print()
        except Exception as hata:
            print(f"  ! Tunel acilamadi: {hata}")
            print("    .env icindeki NGROK_TOKEN dogru mu kontrol et.\n")
    else:
        print("  Tunel : kapali (.env icinde NGROK_TOKEN yok)")
        print("          WhatsApp icin gerekli, web arayuzu icin gerekmiyor.")
        print("=" * 58)
        print()

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
