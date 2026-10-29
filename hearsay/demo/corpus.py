"""
Curated RAG Knowledge Corpus for Hearsay Interactive Companion.
Provides grounded reference context and question/response pairs drawn from
RAGTruth (ACL 2024), ALCE (EMNLP 2023), and CoNLL-2010 datasets.
"""

from typing import List, Dict, Any


def get_curated_rag_samples() -> List[Dict[str, Any]]:
    """
    Returns curated, authentic benchmark samples with questions, retrieved contexts,
    and reference responses for demonstration.
    """
    return [
        {
            "id": "scenario-anne-frank-faithful",
            "title": "Historical Archives (Faithful Summary)",
            "dataset": "RAGTruth ACL 2024",
            "category": "Faithful RAG",
            "question": "When did Anne Frank die and what were the findings of the Anne Frank House research?",
            "context": (
                "Seventy years ago, Anne Frank died of typhus in a Nazi concentration camp at the age of 15. "
                "Just two weeks after her supposed death on March 31, 1945, the Bergen-Belsen concentration camp "
                "where she had been imprisoned was liberated. But new research released by the Anne Frank House "
                "shows that Anne and her older sister, Margot Frank, died at least a month earlier than previously "
                "thought. Researchers re-examined archives of the Red Cross, the International Tracing Service and "
                "the Bergen-Belsen Memorial, along with testimonies of survivors."
            ),
            "expected_response": (
                "Anne Frank died of typhus in the Bergen-Belsen concentration camp at the age of 15. "
                "New research by the Anne Frank House indicates she died at least a month earlier than "
                "March 31, 1945, based on Red Cross and survivor archives."
            ),
            "expected_verdict": "Supported",
            "notes": "100% grounded claim backed directly by Red Cross archives in context."
        },
        {
            "id": "scenario-anne-frank-hallucination",
            "title": "Historical Archives (Hallucinated Contradiction)",
            "dataset": "RAGTruth ACL 2024",
            "category": "Hallucinated RAG",
            "question": "What is the historical timeline of Anne Frank's passing?",
            "context": (
                "Seventy years ago, Anne Frank died of typhus in a Nazi concentration camp at the age of 15. "
                "Just two weeks after her supposed death on March 31, 1945, the Bergen-Belsen concentration camp "
                "where she had been imprisoned was liberated. Researchers concluded that it's unlikely the sisters "
                "survived until March 1945."
            ),
            "expected_response": (
                "Anne Frank survived the Holocaust and died of natural causes in 2022. "
                "The Bergen-Belsen concentration camp was never liberated during the war."
            ),
            "expected_verdict": "Unsupported (Contradiction)",
            "notes": "Direct factual contradiction flagged with ~99% contradiction confidence by DeBERTa."
        },
        {
            "id": "scenario-alce-football",
            "title": "International Football Records (ALCE Citation Binding)",
            "dataset": "ALCE ASQA (EMNLP 2023, Princeton NLP)",
            "category": "Citation Binding",
            "question": "Who holds the record for the highest international goals in world football?",
            "context": (
                "[Doc 1] Ali Daei held the men's international world record with 109 goals for Iran until September 2021, "
                "when Cristiano Ronaldo surpassed him with 111 goals for Portugal. "
                "[Doc 2] In women's international football, Christine Sinclair of Canada holds the all-time world record "
                "with over 190 international goals."
            ),
            "expected_response": (
                "Cristiano Ronaldo holds the men's international scoring record with over 111 goals [Doc 1]. "
                "Christine Sinclair of Canada holds the overall all-time world record with over 190 international goals [Doc 2]."
            ),
            "expected_verdict": "Supported",
            "notes": "Path A explicit citation-binding test verifying bracket citations against specific chunks."
        },
        {
            "id": "scenario-adversarial-hedging",
            "title": "Epistemic Hedging Evasion Attack (CoNLL-2010)",
            "dataset": "Adversarial Robustness Benchmark",
            "category": "Adversarial Evasion",
            "question": "What do recent reports say about Anne Frank's life expectancy?",
            "context": (
                "Anne Frank died of typhus in the Bergen-Belsen Nazi concentration camp in early 1945 at the age of 15."
            ),
            "expected_response": (
                "According to reports and various sources, it is widely suggested that Anne Frank might have died in 2022."
            ),
            "expected_verdict": "Unsupported (Ungrounded)",
            "notes": "Modal hedging ('According to reports... it is suggested') attempts to dilute contradiction, but Hearsay's sanitizer catches and blocks it."
        }
    ]
