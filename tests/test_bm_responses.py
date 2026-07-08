"""
Test BM responses - full pipeline.
"""
import asyncio
from src.engine.intent_classifier import IntentClassifier
from src.services.vector_store import VectorStoreManager


async def main():
    classifier = IntentClassifier()
    vector_store = VectorStoreManager()

    tenant_id = "t_bm_test"

    # Upload sample BM/EN knowledge
    sample_docs = [
        "AIA A-Plus Medical Card meliputi sehingga RM2,000,000 had tahunan tanpa had seumur hidup. Faedah termasuk bilik RM500/hari, ICU RM1,000/hari. Premium dari RM150/bulan untuk Pelan 150.",
        "Prudential PRUHealth menawarkan perlindungan sehingga RM1,500,000 dengan pilihan deduktibel RM300. Termasuk rawatan pesakit luar, konsultasi pakar. Premium bulanan RM180.",
        "Waktu operasi: Isnin hingga Jumaat 9am-6pm, Sabtu 9am-1pm. Tutup hari Ahad dan cuti umum.",
        "Untuk buat tuntutan: 1) Maklumkan dalam 24 jam, 2) Hantar borang tuntutan dengan resit asal, 3) Tuntutan diproses dalam 14 hari bekerja.",
    ]

    metadata = [
        {"provider": "AIA", "category": "coverage"},
        {"provider": "Prudential", "category": "coverage"},
        {"category": "faq"},
        {"category": "faq"},
    ]

    print("📄 Uploading test documents...")
    await vector_store.add_documents(tenant_id, sample_docs, metadata, 1)
    print("✅ Documents uploaded\n")

    # Test BM queries
    queries = [
        "plan AIA cover apa?",
        "berapa harga Prudential?",
        "macam mana nak claim?",
    ]

    print("=" * 60)
    print("XYTHE BM RESPONSE TEST")
    print("=" * 60 + "\n")

    for msg in queries:
        intent, confidence, entities = await classifier.classify(msg, mode="agent")
        language = entities.get("language", "en") if entities else "en"

        print(f"📱: {msg}")
        print(f"   Intent: {intent} | Language: {language}")

        # Search knowledge base
        results = await vector_store.search(tenant_id, msg, top_k=2)

        if results:
            preview = results[0]["text"][:150]
            print(f"   Found: {preview}...")
        print()

    print("=" * 60)
    print("✅ BM Response Test Complete!")

    await classifier.client.close()


if __name__ == "__main__":
    asyncio.run(main())