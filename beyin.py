"""
Beyin
-----
Butun kanallarin ortak cevap uretme yeri.

WhatsApp, Telegram, web arayuzu -> hepsi buraya gelir.
Yeni bir kanal eklerken burayi degistirmezsin, sadece cagirirsin.
"""

GECMIS_SINIRI = 12   # kisi basina saklanan mesaj sayisi


def cevapla(depo: dict, kimlik: str, soru: str, etiket: str = "") -> str:
    """Bir kisinin sorusuna, onceki konusmasini da dikkate alarak cevap uretir.

    depo    : konusmalarin tutuldugu sozluk (her kanalin kendi deposu olur)
    kimlik  : kisiyi ayirt eden deger (telefon numarasi, telegram id, ...)
    soru    : musterinin yazdigi metin
    etiket  : log satirlarinda gorunecek kanal adi
    """
    from app import MODEL, client, sistem_metni

    gecmis = depo.setdefault(kimlik, [])
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
    except Exception:
        gecmis.pop()          # basarisiz soruyu gecmiste birakma
        raise

    cevap = "".join(p.text for p in yanit.content if p.type == "text").strip()
    gecmis.append({"role": "assistant", "content": cevap})

    k = yanit.usage
    print(f"  [{etiket}] {kimlik} | giris:{k.input_tokens} cikis:{k.output_tokens}")
    print(f"           soru : {soru[:70]}")
    print(f"           cevap: {cevap[:70]}")
    return cevap


def sifirla(depo: dict, kimlik: str) -> None:
    depo.pop(kimlik, None)
