"""
Full pipeline test.
Simulates: Customer WhatsApps → Xythe processes → Xythe replies
"""
import asyncio
from src.config import settings
from src.engine.intent_classifier import IntentClassifier
from src.services.vector_store import VectorStoreManager
from src.utils.logging import logger


async def main():
    print("\n" + "="*60)
    print("XYTHE FULL PIPELINE TEST")
    print("="*60 + "\n")

    classifier = IntentClassifier()
    vector_store = VectorStoreManager()

    # Step 1: Simulate uploading a document (Farah's AIA brochure)
    print("📄 STEP 1: Simulating document upload...")
    tenant_id = "t_test01"

    sample_doc = [
        "AIA A-Plus Medical Card provides comprehensive coverage up to RM2,000,000 annual limit with no lifetime cap. Benefits include room and board up to RM500 per day, ICU coverage of RM1,000 per day, and surgical expenses as charged. Premium for age 30-35 starts from RM150 per month for Plan 150.",
        
        "Prudential PRUHealth medical plan offers coverage up to RM1,500,000 with a RM300 deductible option. Includes outpatient treatment, specialist consultations, and emergency medical evacuation. Monthly premium for age 30-35 is RM180 for basic coverage.",
        
        "Great Eastern SmartMedic provides RM1,000,000 annual coverage with guaranteed renewal up to age 80. Features include no claim bonus, daily hospital cash allowance of RM200, and coverage for 11 critical illnesses. Premium from RM130/month.",
        
        "Business hours: Monday to Friday 9am-6pm, Saturday 9am-1pm. Closed on Sundays and public holidays. Contact: +60123456789 for urgent inquiries.",
        
        "To make a claim: 1) Notify us within 24 hours, 2) Submit claim form with original receipts, 3) Claims processed within 14 working days. Direct billing available at panel hospitals.",
    ]

    metadata_list = [
        {"provider": "AIA", "product": "A-Plus Medical", "category": "coverage"},
        {"provider": "Prudential", "product": "PRUHealth", "category": "coverage"},
        {"provider": "Great Eastern", "product": "SmartMedic", "category": "coverage"},
        {"provider": "general", "product": "general", "category": "faq"},
        {"provider": "general", "product": "general", "category": "faq"},
    ]

    await vector_store.add_documents(
        tenant_id=tenant_id,
        chunks=sample_doc,
        metadata_list=metadata_list,
        document_id=1
    )
    print("   ✅ 5 document chunks uploaded and embedded\n")

    # Step 2: Simulate customer messages
    test_conversations = [
        {
            "customer": "Ali",
            "message": "What does AIA medical card cover?",
            "expected": "Should find AIA coverage details"
        },
        {
            "customer": "Siti",
            "message": "How much is Prudential per month?",
            "expected": "Should find Prudential pricing"
        },
        {
            "customer": "Muthu",
            "message": "Compare AIA and Great Eastern please",
            "expected": "Should find both providers"
        },
        {
            "customer": "Mei Ling",
            "message": "How do I make a claim?",
            "expected": "Should find claims process"
        },
    ]

    print("📱 STEP 2: Processing customer messages...\n")

    for conv in test_conversations:
        print(f"👤 {conv['customer']}: \"{conv['message']}\"")
        
        # Classify intent
        intent, confidence, entities = await classifier.classify(
            conv['message'], mode="agent"
        )
        print(f"   🧠 Intent: {intent} ({confidence:.0%})")
        
        # Search knowledge base
        results = await vector_store.search(
            tenant_id=tenant_id,
            query=conv['message'],
            top_k=2
        )
        
        if results:
            print(f"   📚 Found {len(results)} relevant chunks:")
            for i, r in enumerate(results):
                preview = r['text'][:120] + "..."
                print(f"      {i+1}. [score: {r['score']}] {preview}")
        else:
            print(f"   ❌ No relevant information found")
        
        print()

    # Step 3: Stats
    stats = vector_store.get_stats(tenant_id)
    print("="*60)
    print(f"📊 Vector store: {stats['total_chunks']} chunks indexed")
    print("="*60)
    print("\n✅ Full pipeline test complete!")

    await classifier.client.close()


if __name__ == "__main__":
    asyncio.run(main())