"""
hearsay.ui.dashboard: Interactive Streamlit Observability Dashboard for Hearsay.
Provides real-time KPI metrics, historical claim-to-evidence audit inspection,
and a live verification sandbox.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional

from hearsay.db import TraceStore
from hearsay.proxy.protocol import VerificationRequest, ContextPayload
from hearsay.proxy.gateway import _execute_verification

# --- Page Configuration & Styling ---
st.set_page_config(
    page_title="Hearsay Observability Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .metric-card {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 16px;
            border: 1px solid #e9ecef;
        }
        .claim-card {
            padding: 14px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 6px solid #ccc;
        }
        .claim-supported {
            background-color: #e6f4ea;
            border-left-color: #137333;
            color: #0d381e;
        }
        .claim-ungrounded {
            background-color: #fef7e0;
            border-left-color: #b06000;
            color: #482900;
        }
        .claim-contradicted {
            background-color: #fce8e6;
            border-left-color: #c5221f;
            color: #4a0d0b;
        }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 8px;
        }
        .badge-verified {
            background-color: #137333;
            color: white;
        }
        .badge-hallucination {
            background-color: #c5221f;
            color: white;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_db() -> TraceStore:
    """Instantiates a cached instance of the TraceStore."""
    return TraceStore("hearsay_traces.db")


db = get_db()

# --- Header ---
st.title("🛡️ Hearsay: RAG Groundedness Observability")
st.caption("Sentence-level hallucination detection, claim-to-evidence alignment & audit telemetry")

# --- Top KPI Metrics Banner ---
metrics = db.get_metrics_summary()

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
with kpi1:
    st.metric("Total Requests", f"{metrics['total_requests']}")
with kpi2:
    st.metric("Pass Rate", f"{metrics['verification_pass_rate']}%")
with kpi3:
    st.metric("Avg Groundedness", f"{metrics['avg_groundedness_score']}%")
with kpi4:
    st.metric("Avg Latency", f"{metrics['avg_latency_ms']} ms")
with kpi5:
    st.metric("Hallucinations Caught", f"{metrics['total_hallucinations']}")

st.divider()

# --- Navigation Tabs ---
tab_traces, tab_sandbox, tab_analytics = st.tabs([
    "🔍 Trace Explorer & Evidence Map",
    "⚡ Live Verification Sandbox",
    "📈 Claims & Reliability Analytics"
])

# ==========================================
# TAB 1: Trace Explorer & Evidence Map
# ==========================================
with tab_traces:
    # Sidebar Filters
    st.sidebar.header("🔍 Trace Filters")
    status_filter_opt = st.sidebar.selectbox(
        "Filter by Status",
        options=["All", "Verified", "Hallucination Detected"]
    )
    status_arg = None if status_filter_opt == "All" else status_filter_opt
    limit_arg = st.sidebar.slider("Max Traces to Load", min_value=10, max_value=100, value=50, step=10)

    if st.sidebar.button("🔄 Refresh Data"):
        st.rerun()

    traces = db.get_recent_traces(limit=limit_arg, status_filter=status_arg)

    if not traces:
        st.info("No traces found matching the current filter. Send requests to the Gateway or use the Sandbox tab!")
    else:
        # Build selectable options
        trace_map = {
            f"[{t['request_id']}] {t['overall_status']} | Score: {t['groundedness_score']}% | {t['timestamp'][:19]}": t['request_id']
            for t in traces
        }
        selected_label = st.selectbox("Select a Verification Request to Inspect:", options=list(trace_map.keys()))
        selected_id = trace_map[selected_label]

        trace = db.get_trace(selected_id)
        if trace:
            result_data = trace.get("result", {})

            # Request summary metadata
            badge_class = "badge-verified" if trace['overall_status'] == "Verified" else "badge-hallucination"
            st.markdown(
                f"""
                ### Request ID: `#{trace['request_id']}` 
                <span class="badge {badge_class}">{trace['overall_status']}</span>
                """,
                unsafe_allow_html=True,
            )

            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.write(f"**Timestamp:** `{trace['timestamp'][:19]}`")
            m_col2.write(f"**Source Document ID:** `{trace['source_id']}`")
            m_col3.write(f"**Groundedness Score:** `{trace['groundedness_score']}%`")
            m_col4.write(f"**Latency:** `{trace['latency_ms']} ms`")

            # Model Response Text
            st.markdown("#### 💬 Model Generated Response")
            st.text_area("Full Response Prose", value=trace["response_text"], height=90, disabled=True)

            # Claim-level Evidence Breakdown
            st.markdown("#### 🔬 Sentence-Level Claim & Evidence Breakdown")
            claims = result_data.get("claims", [])

            if not claims:
                st.write("No individual claims extracted.")
            else:
                for claim in claims:
                    status = claim.get("status", "Unknown")
                    confidence = round(float(claim.get("confidence", 0.0)) * 100, 1)

                    if status == "Supported":
                        card_class = "claim-supported"
                        icon = "🟢"
                    elif "Contradiction" in status:
                        card_class = "claim-contradicted"
                        icon = "🔴"
                    else:
                        card_class = "claim-ungrounded"
                        icon = "🟡"

                    evidence = claim.get("evidence_span") or "No supporting evidence found in source context."
                    source_chunk = claim.get("source_chunk_id") or trace["source_id"]

                    st.markdown(
                        f"""
                        <div class="claim-card {card_class}">
                            <strong>{icon} Claim #{claim.get('claim_id', 0) + 1}:</strong> "{claim.get('claim_text')}"<br>
                            <strong>Status:</strong> {status} &nbsp;|&nbsp; <strong>Confidence:</strong> {confidence}%<br>
                            <strong>Retrieved Evidence ({source_chunk}):</strong> <em>"{evidence}"</em>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

# ==========================================
# TAB 2: Live Verification Sandbox
# ==========================================
with tab_sandbox:
    st.subheader("⚡ Live RAG Groundedness Playground")
    st.write("Test Hearsay's verification engine against custom context and LLM outputs in real time.")

    col_in1, col_in2 = st.columns(2)
    with col_in1:
        sandbox_source_id = st.text_input("Source Document ID", value="doc_wiki_apollo11")
        sandbox_context = st.text_area(
            "Retrieved Reference Context (Source Ground Truth)",
            value="Apollo 11 launched on July 16, 1969. Commander Neil Armstrong and Lunar Module pilot Buzz Aldrin landed the Apollo Lunar Module Eagle on the Moon on July 20, 1969. Armstrong became the first person to step onto the lunar surface six hours and 39 minutes later on July 21.",
            height=180,
        )

    with col_in2:
        st.write("&nbsp;")
        sandbox_response = st.text_area(
            "LLM Assistant Response to Verify",
            value="Apollo 11 launched on July 16, 1969. Neil Armstrong was the first person to step on the lunar surface. The mission landed on Mars in 1975.",
            height=180,
        )

    if st.button("🚀 Verify Groundedness", type="primary"):
        if not sandbox_context.strip() or not sandbox_response.strip():
            st.error("Please provide both reference context and response text.")
        else:
            with st.spinner("Analyzing claims and aligning evidence..."):
                ctx = ContextPayload(source_id=sandbox_source_id.strip(), source_info=sandbox_context.strip())
                res = _execute_verification(sandbox_response.strip(), ctx)

                # Persist to database so it immediately shows up in the audit log
                db.log_trace(res, sandbox_response.strip(), ctx.source_id)

            st.success(f"Verification Complete! Status: {res.overall_status} ({res.groundedness_score}% grounded)")

            # Render immediate breakdown
            sb_col1, sb_col2, sb_col3 = st.columns(3)
            sb_col1.metric("Groundedness Score", f"{res.groundedness_score}%")
            sb_col2.metric("Supported Claims", f"{res.supported_claims}/{res.total_claims}")
            sb_col3.metric("Latency", f"{res.latency_ms} ms")

            for c in res.claims:
                icon = "🟢" if c.status == "Supported" else ("🔴" if "Contradiction" in c.status else "🟡")
                color = "#e6f4ea" if c.status == "Supported" else ("#fce8e6" if "Contradiction" in c.status else "#fef7e0")
                evidence_text = c.evidence_span or "No supporting evidence found."

                st.markdown(
                    f"""
                    <div style="background-color: {color}; padding: 12px; border-radius: 8px; margin-bottom: 8px; color: #111;">
                        <strong>{icon} Claim:</strong> {c.claim_text}<br>
                        <strong>Status:</strong> {c.status} (Confidence: {round(c.confidence * 100, 1)}%)<br>
                        <small><strong>Evidence:</strong> <em>"{evidence_text}"</em></small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# ==========================================
# TAB 3: Claims & Reliability Analytics
# ==========================================
with tab_analytics:
    st.subheader("📈 Groundedness & Claim Distribution")

    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.markdown("#### Overall Claim Statistics")
        claims_df = pd.DataFrame({
            "Claim Type": ["Supported Claims", "Contradicted Claims", "Ungrounded Claims"],
            "Count": [metrics["total_supported"], metrics["total_contradicted"], metrics["total_ungrounded"]],
        })
        st.dataframe(claims_df, hide_index=True, use_container_width=True)

        if metrics["total_claims"] > 0:
            st.bar_chart(claims_df.set_index("Claim Type"))

    with col_a2:
        st.markdown("#### Gateway Verification Outcomes")
        outcomes_df = pd.DataFrame({
            "Outcome": ["Verified (100% Grounded)", "Hallucinations Detected"],
            "Count": [metrics["total_verified"], metrics["total_hallucinations"]],
        })
        st.dataframe(outcomes_df, hide_index=True, use_container_width=True)

        if metrics["total_requests"] > 0:
            st.bar_chart(outcomes_df.set_index("Outcome"))
