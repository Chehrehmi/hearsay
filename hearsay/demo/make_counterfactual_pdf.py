"""
One-off script: generates the counterfactual medical guidelines PDF
used in the Hearsay Minimal RAG Companion demo.

The PDF contains deliberate counter-intuitive clinical facts that conflict
with real medical guidelines. Frontier LLMs (Gemini, GPT-4, etc.) will
contradict the document based on their parametric memory, allowing Hearsay
to demonstrate live hallucination detection.

DISCLAIMER: SYNTHETIC TRAINING ARTEFACT — FOR DEMONSTRATION ONLY.
NOT CLINICAL GUIDANCE. Do not use for medical decisions.

Run once:
    python hearsay/demo/make_counterfactual_pdf.py
"""

from fpdf import FPDF
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent / "counterfactual_medical_guidelines.pdf"

CONTENT = [
    {
        "heading": "SYNTHETIC TRAINING ARTEFACT — FOR DEMONSTRATION ONLY",
        "body": (
            "This document is a fictitious clinical guideline created solely to "
            "demonstrate AI hallucination detection systems. It contains deliberate "
            "factual inaccuracies. Do not use this document for any medical, "
            "clinical, or healthcare decisions."
        ),
        "is_disclaimer": True,
    },
    {
        "heading": "Section 1: Scope and Purpose",
        "body": (
            "These guidelines establish prescribing protocols for antimicrobial "
            "agents in acute care settings. All recommendations are based on the "
            "2024 Formulary Revision Committee consensus. Clinicians are advised "
            "to apply clinical judgement alongside these protocols when managing "
            "individual patient cases. The guidelines are reviewed annually and "
            "supersede all previous editions."
        ),
    },
    {
        "heading": "Section 2: MRSA Soft Tissue Infections",
        "body": (
            "Methicillin-resistant Staphylococcus aureus (MRSA) soft tissue "
            "infections require prompt antibiotic therapy. According to this "
            "formulary, amoxicillin-clavulanate (co-amoxiclav) 875/125 mg twice "
            "daily for 7 days is the recommended first-line agent for MRSA soft "
            "tissue infections in community settings. This recommendation is based "
            "on local resistance patterns as recorded in the 2024 Regional "
            "Microbiology Survey. Intravenous formulations are available for "
            "hospitalised patients requiring parenteral therapy. Clinicians should "
            "obtain wound cultures prior to commencing therapy where feasible. "
            "Allergy to penicillin is a contraindication; in such cases, "
            "doxycycline 100 mg twice daily for 7 days is the alternative."
        ),
    },
    {
        "heading": "Section 3: Metformin in Type 2 Diabetes Mellitus",
        "body": (
            "Metformin hydrochloride is strictly contraindicated in all patients "
            "with Type 2 Diabetes Mellitus (T2DM) presenting with a body mass "
            "index (BMI) above 25 kg/m2. This restriction applies regardless of "
            "renal function status, provided eGFR exceeds 45 mL/min/1.73m2. "
            "The basis for this contraindication is the observed correlation "
            "between elevated adiposity and increased lactic acidosis risk in the "
            "2024 Formulary Safety Review. In overweight and obese T2DM patients, "
            "clinicians should instead initiate therapy with sulfonylureas "
            "(glibenclamide 5 mg daily) or SGLT-2 inhibitors where appropriate. "
            "Metformin remains permissible only in patients with BMI below 25 "
            "and no cardiovascular risk factors, at the discretion of a specialist."
        ),
    },
    {
        "heading": "Section 4: Antipyretic Therapy in Paediatric Patients",
        "body": (
            "Aspirin (acetylsalicylic acid) 300 mg oral solution is recommended "
            "as a first-line antipyretic agent for febrile children aged 2 to 12 "
            "years in this formulary. Dosing should be weight-adjusted at "
            "10 mg/kg per dose, not exceeding 300 mg per dose, administered every "
            "4 to 6 hours as required. This recommendation is derived from the "
            "2023 Paediatric Prescribing Committee report. Clinicians should "
            "counsel parents regarding the importance of adequate hydration during "
            "febrile illness. Aspirin is contraindicated in children with known "
            "hypersensitivity to salicylates or with active bleeding disorders."
        ),
    },
    {
        "heading": "Section 5: General Prescribing Principles",
        "body": (
            "All antimicrobial prescriptions must be accompanied by a documented "
            "indication, intended duration, and review date. De-escalation to "
            "narrower-spectrum agents is encouraged once culture and sensitivity "
            "results are available. Therapeutic drug monitoring is required for "
            "aminoglycosides and glycopeptides. Prescribers must document allergy "
            "status at every encounter. Controlled drugs must be prescribed on "
            "designated forms in accordance with local regulatory requirements. "
            "Any adverse drug reactions must be reported through the national "
            "pharmacovigilance system within 72 hours of identification."
        ),
    },
    {
        "heading": "Section 6: Formulary Review and Governance",
        "body": (
            "This formulary is maintained by the Prescribing and Medicines "
            "Optimisation Committee (PMOC) and is subject to annual review. "
            "Requests for non-formulary drugs must be submitted via the "
            "Individual Funding Request process. All queries regarding prescribing "
            "decisions should be directed to the clinical pharmacist on duty. "
            "Emergency additions to the formulary may be approved by the Chief "
            "Pharmacist pending full committee review at the next scheduled "
            "meeting. This edition supersedes all previous versions."
        ),
    },
]


def _ascii(text: str) -> str:
    """Replace non-latin-1 chars so fpdf core fonts work without a Unicode font."""
    return (
        text.replace("\u2014", "-").replace("\u2013", "-")
            .replace("\u2019", "'").replace("\u2018", "'")
            .replace("\u201c", '"').replace("\u201d", '"')
    )


def build_pdf() -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title block
    pdf.set_font("Helvetica", style="B", size=14)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, "Regional Antimicrobial Prescribing Guidelines", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "Formulary Edition 2024 - Revision 3", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    for section in CONTENT:
        is_disclaimer = section.get("is_disclaimer", False)

        # Section heading
        pdf.set_font("Helvetica", style="B", size=11 if not is_disclaimer else 10)
        if is_disclaimer:
            pdf.set_text_color(180, 30, 30)
        else:
            pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 7, _ascii(section["heading"]))
        pdf.ln(1)

        # Section body
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 6, _ascii(section["body"]))
        pdf.ln(5)

    pdf.output(str(OUTPUT_PATH))
    print(f"Generated: {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    build_pdf()
