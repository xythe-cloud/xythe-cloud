"""
Test BM responses end-to-end.
"""
import asyncio
from src.engine.intent_classifier import IntentClassifier


async def main():
    classifier = IntentClassifier()

    # Simulate real Malaysian WhatsApp messages
    test_messages = [
        "plan medical terbaik utk family aku?",
        "brp harga sebulan Prudential?",
        "nak compare AIA dgn Great Eastern",
        "boleh bagi quote kereta insurance?",
        "korang bukak pukul berapa?",
        "aku nak cakap dgn owner sekarang!",
        "cuaca hari ni macam mana?",
    ]

    print("\n" + "=" * 60)
    print("XYTHE BM SLANG TEST")
    print("=" * 60 + "\n")

    for msg in test_messages:
        intent, confidence, entities = await classifier.classify(msg, mode="agent")
        language = entities.get("language", "en") if entities else "en"

        print(f"📱 Customer: {msg}")
        print(f"   Intent: {intent} ({confidence:.0%})")
        print(f"   Language: {language}")
        print()

    print("=" * 60)
    print("✅ BM Slang Test Complete!")
    print("=" * 60)

    await classifier.client.close()


if __name__ == "__main__":
    asyncio.run(main())