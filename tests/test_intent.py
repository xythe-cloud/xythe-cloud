"""
Quick test of the intent classifier.
No server needed - runs directly.
"""
import asyncio
from src.engine.intent_classifier import IntentClassifier


async def main():
    classifier = IntentClassifier()

    # Test messages (simulating real customer WhatsApps)
    test_messages = [
        "What does AIA medical card cover for family?",
        "How much is Prudential life insurance monthly?",
        "Compare AIA vs Great Eastern medical plan",
        "Can I get a quotation for car insurance?",
        "What time do you open?",
        "I want to speak to a real person now, this is useless",
        "What's the weather like today?",
    ]

    print("\n" + "="*60)
    print("XYTHE INTENT CLASSIFIER - TEST")
    print("="*60 + "\n")

    for msg in test_messages:
        intent, confidence, entities = await classifier.classify(msg, mode="agent")
        print(f"📱 Customer: {msg}")
        print(f"   Intent: {intent} ({confidence:.0%})")
        print(f"   Entities: {entities}")
        print()

    print("="*60)
    print("Test complete!")
    print("="*60)

    await classifier.client.close()


if __name__ == "__main__":
    asyncio.run(main())