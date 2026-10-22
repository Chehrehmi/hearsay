"""
tests.test_ui: Automated headless integration tests for the Hearsay Streamlit Dashboard.
"""

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

# Resolve absolute path to dashboard.py regardless of where pytest is invoked
DASHBOARD_PATH = (Path(__file__).parent.parent / "hearsay" / "ui" / "dashboard.py").resolve()


def test_dashboard_file_exists():
    assert DASHBOARD_PATH.exists()
    assert DASHBOARD_PATH.is_file()


def test_dashboard_renders_without_exceptions():
    at = AppTest.from_file(str(DASHBOARD_PATH), default_timeout=15)
    at.run()
    assert not at.exception, f"Dashboard threw unexpected exception: {at.exception}"


def test_dashboard_title_and_kpi_metrics():
    at = AppTest.from_file(str(DASHBOARD_PATH), default_timeout=15)
    at.run()
    
    # Verify title is displayed
    assert len(at.title) > 0
    assert "Hearsay" in at.title[0].value

    # Verify all 5 top KPI metrics render
    assert len(at.metric) >= 5
    metric_labels = [m.label for m in at.metric]
    assert "Total Requests" in metric_labels
    assert "Pass Rate" in metric_labels
    assert "Avg Groundedness" in metric_labels
    assert "Avg Latency" in metric_labels
    assert "Hallucinations Caught" in metric_labels
