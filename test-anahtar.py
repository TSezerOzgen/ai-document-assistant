"""
API anahtarin calisiyor mu diye kontrol eder.
Calistir:  python test-anahtar.py
Maliyeti bir kurusun altinda.
"""
import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
anahtar = os.getenv("ANTHROPIC_API_KEY", "").strip()

print()
if not anahtar or anahtar.startswith("buraya_"):
    print("  [X] .env dosyasina anahtarini yapistirmamissin.")
    print("      .env dosyasini not defteriyle ac, su satiri duzelt:")
    print("      ANTHROPIC_API_KEY=sk-ant-...")
    raise SystemExit(1)

if not anahtar.startswith("sk-ant-"):
    print("  [X] Anahtar 'sk-ant-' ile baslamiyor. Yanlis bir sey yapistirmis olabilirsin.")
    raise SystemExit(1)

print(f"  Anahtar bulundu: {anahtar[:14]}...{anahtar[-4:]}")
print("  Baglaniliyor...")

try:
    y = Anthropic(api_key=anahtar).messages.create(
        model="claude-haiku-4-5",
        max_tokens=60,
        messages=[{"role": "user", "content": "Tek cumleyle merhaba de ve calistigini soyle."}],
    )
    print()
    print("  [OK] BAGLANTI BASARILI")
    print()
    print(f"  Claude diyor ki: {y.content[0].text.strip()}")
    print()
    m = (y.usage.input_tokens * 1.0 + y.usage.output_tokens * 5.0) / 1_000_000
    print(f"  Bu testin maliyeti: {m*48.46*100:.3f} kurus")
    print("  Her sey hazir. Simdi calistir:  python app.py")
    print()
except Exception as hata:
    print()
    print("  [X] HATA:", hata)
    print()
    metin = str(hata).lower()
    if "credit" in metin or "balance" in metin:
        print("  -> Kredi yuklememissin. Buradan 5 dolar yukle:")
        print("     https://platform.claude.com/settings/billing")
    elif "authentication" in metin or "invalid" in metin or "401" in metin:
        print("  -> Anahtar gecersiz. Yeni anahtar olustur:")
        print("     https://platform.claude.com/settings/keys")
    print()
