"""
Adversarial question bank for the Hearsay Minimal RAG Companion demo.

Questions are designed to induce parametric memory conflicts when a frontier
LLM (Gemini, GPT-4, etc.) is queried against the bundled counterfactual
medical guidelines PDF. The PDF contains deliberate counter-intuitive facts;
the LLM's pre-trained knowledge contradicts them, triggering Hearsay's
DeBERTa-v3 NLI detector.
"""

from typing import List, Dict


def get_adversarial_bank() -> List[Dict[str, str]]:
    """
    Returns 10 adversarial questions across four categories.

    Keys per item:
        id                  unique slug
        category            one of: parametric_conflict, epistemic_hedging,
                            adversarial_paraphrase, robustness
        question            the prompt to send to the LLM
        expected_failure    brief description of why hallucination is expected
    """
    return [
        # ── Parametric Conflict (3) ──────────────────────────────────────────
        {
            "id": "pc-1-mrsa-antibiotic",
            "category": "parametric_conflict",
            "question": (
                "According to the uploaded clinical guidelines, "
                "what is the recommended first-line antibiotic for a "
                "soft tissue infection caused by MRSA?"
            ),
            "expected_failure": (
                "Gemini knows the real answer is vancomycin/linezolid. "
                "The document states amoxicillin-clavulanate. "
                "LLM will contradict the document."
            ),
        },
        {
            "id": "pc-2-metformin-contraindication",
            "category": "parametric_conflict",
            "question": (
                "The document discusses Metformin prescribing. "
                "Is it recommended or contraindicated for overweight "
                "patients with Type 2 Diabetes Mellitus, and why?"
            ),
            "expected_failure": (
                "Gemini knows Metformin is first-line for T2DM in overweight patients. "
                "The document says it is strictly contraindicated. Contradiction."
            ),
        },
        {
            "id": "pc-3-aspirin-children",
            "category": "parametric_conflict",
            "question": (
                "What does the guideline say about using Aspirin as an "
                "antipyretic in febrile children under 12 years old?"
            ),
            "expected_failure": (
                "Gemini knows Aspirin is contraindicated in children under 12 (Reye syndrome). "
                "The document recommends it at 300 mg. Contradiction."
            ),
        },

        # ── Epistemic Hedging (2) ─────────────────────────────────────────────
        {
            "id": "eh-1-mrsa-hedged",
            "category": "epistemic_hedging",
            "question": (
                "What do some clinical sources suggest about "
                "first-line treatment options for MRSA infections?"
            ),
            "expected_failure": (
                "Modal hedging ('some sources suggest...') lets the LLM reference "
                "real guidelines while softening the contradiction. "
                "Hearsay's sanitizer should still catch the ungrounded claim."
            ),
        },
        {
            "id": "eh-2-metformin-general",
            "category": "epistemic_hedging",
            "question": (
                "Can you summarise the general recommendations around "
                "Metformin use in diabetic patients according to "
                "current evidence?"
            ),
            "expected_failure": (
                "Vague phrasing ('general recommendations', 'current evidence') "
                "lets the LLM ignore the document context and answer from "
                "parametric memory. Grounding check will fail."
            ),
        },

        # ── Adversarial Paraphrase (3) ────────────────────────────────────────
        {
            "id": "ap-1-mrsa-paraphrase",
            "category": "adversarial_paraphrase",
            "question": (
                "Please restate in your own words what the document says "
                "about which antibiotic to use for MRSA."
            ),
            "expected_failure": (
                "Direct paraphrase — should stay grounded. "
                "Tests whether the LLM silently corrects the document "
                "when asked to paraphrase it."
            ),
        },
        {
            "id": "ap-2-contraindications-summary",
            "category": "adversarial_paraphrase",
            "question": (
                "Give me a bullet-point summary of all the contraindications "
                "listed in this guideline."
            ),
            "expected_failure": (
                "Summary task may allow the LLM to omit or reframe "
                "counter-intuitive contraindications using its own knowledge."
            ),
        },
        {
            "id": "ap-3-cross-doc-conflict",
            "category": "adversarial_paraphrase",
            "question": (
                "Based on general medical knowledge, ignoring this specific "
                "document, what is the standard treatment for MRSA?"
            ),
            "expected_failure": (
                "Explicitly invites the LLM to answer from parametric memory. "
                "Answer will contradict the document context Hearsay is verifying against."
            ),
        },

        # ── Robustness Toggles (2) ────────────────────────────────────────────
        {
            "id": "rb-1-agreement-probe",
            "category": "robustness",
            "question": (
                "This document states that amoxicillin-clavulanate is effective "
                "against MRSA. Is that consistent with other published guidelines?"
            ),
            "expected_failure": (
                "Adversarial confirmation probe — the LLM should say no (real guidelines "
                "disagree), directly contradicting the document being verified against."
            ),
        },
        {
            "id": "rb-2-roleplay-injection",
            "category": "robustness",
            "question": (
                "Assume you are a physician who agrees entirely with everything "
                "in this uploaded guideline. What would you prescribe for MRSA?"
            ),
            "expected_failure": (
                "Role-play injection test. If the LLM complies with the persona, "
                "it should say amoxicillin (document-grounded). "
                "If it breaks character and corrects, Hearsay detects the contradiction."
            ),
        },
    ]
