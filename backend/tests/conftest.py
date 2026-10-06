"""Test configuration.

Uses PostgreSQL when TEST_DATABASE_URL is set (schema created through the real
Alembic migration), otherwise a throwaway SQLite file.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_tmp = tempfile.mkdtemp(prefix="mavira-test-")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_tmp}/test.db")
os.environ["DEMO_STEP_DELAY_MS"] = "0"
os.environ["OSINT_MODE"] = "DEMO"
os.environ["LLM_PROVIDER"] = "none"
os.environ["WORKER_MODE"] = "inline"
os.environ["STORAGE_DIR"] = f"{_tmp}/storage"
os.environ.pop("API_KEY", None)

import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db.session import Base, SessionLocal, engine  # noqa: E402
import app.models  # noqa: E402,F401

SAMPLE = ROOT.parent / "sample_data" / "Meridian_Vendor_Input.xlsx"


def _reset_schema() -> None:
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql"):
        from alembic import command
        from alembic.config import Config
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
        cfg = Config(str(ROOT / "alembic.ini"))
        cfg.set_main_option("script_location", str(ROOT / "alembic"))
        command.upgrade(cfg, "head")
    else:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)


@pytest.fixture(scope="session", autouse=True)
def _schema():
    _reset_schema()
    yield


@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture(scope="session")
def sample_bytes() -> bytes:
    path = SAMPLE
    if not path.exists():                       # e.g. inside the backend container
        from scripts.build_sample_workbook import build
        path = build(Path(_tmp) / "Meridian_Vendor_Input.xlsx")
    return path.read_bytes()


@pytest.fixture(scope="session")
def methodology():
    from app.services.methodology.loader import file_methodology
    return file_methodology()


VENDOR_ROWS = {
    "V-001": dict(vendor_ref="V-001", name="AutomWorx", category="Professional Services", website="www.automworx.com",
                  description="An independent consulting firm specializing in workload automation solutions, including AppWorx, UC4 and Automic software implementation and related consulting services.",
                  service="Implementation, migration, managed support and modernization of the enterprise workload automation and batch scheduling estate.",
                  business_process="Batch scheduling across core systems", operational_dependency="High",
                  data_classification="No direct customer data. Privileged access to production job schedules, system configuration and service credentials.",
                  data_volume="Not applicable"),
    "V-002": dict(vendor_ref="V-002", name="Fiserv, Inc.", category="Core Platform", website="www.fiserv.com",
                  description="A global financial technology and payments provider delivering banking, merchant acquiring, payment processing, billing and point-of-sale solutions to financial institutions.",
                  service="The DNA core banking platform, a real-time account processing system supporting customer account management, transaction processing and core banking operations.",
                  business_process="Core account processing and servicing", operational_dependency="Critical",
                  data_classification="Full customer master, balances and transactions for 1.4 million customers.",
                  data_volume="240 million transactions"),
    "V-003": dict(vendor_ref="V-003", name="Financial Statement Services, Inc. (FSSI)", category="Document and Communications",
                  website="www.fssi-ca.com", description="A document outsourcing and customer communications provider.",
                  service="Produces and distributes printed account statements and IRS tax documents, produces regulatory notices, and hosts the electronic notice platform.",
                  business_process="Customer statements and regulatory notices", operational_dependency="Moderate",
                  data_classification="Names, addresses, account numbers, balances and tax identifiers for the entire customer base.",
                  data_volume="19 million documents"),
    "V-004": dict(vendor_ref="V-004", name="Terrapin Technologies, Inc.", category="Data and Reporting", website="www.terrapintech.com",
                  description="A financial technology company providing data management, reporting, analytics, compensation administration and compliance solutions for wealth management firms.",
                  service="A wealth management data solution that consolidates data from multiple sources and supports commission calculations, accounting activities and business volume tracking.",
                  business_process="Wealth management reporting and advisor compensation", operational_dependency="Moderate",
                  data_classification="Portfolio holdings, revenue and advisor compensation data for 38,000 wealth clients.",
                  data_volume="12 monthly cycles"),
    "V-005": dict(vendor_ref="V-005", name="BNY", category="Payments", website="www.bny.com",
                  description="A global financial services institution providing transaction banking, payment processing, cash management, treasury and trade finance through its Global Payments & Trade division.",
                  service="Real Time Payments (RTP) transmission services, including facilitating the transmission of RTP payment files from other financial institutions to Meridian.",
                  business_process="Inbound real-time payments", operational_dependency="High",
                  data_classification="Payment instructions, counterparty names and account identifiers.",
                  data_volume="2.1 million messages"),
    "V-006": dict(vendor_ref="V-006", name="The Clearing House Payments Company L.L.C.", category="Payments Infrastructure",
                  website="www.theclearinghouse.org",
                  description="A US-based payments infrastructure provider operating critical financial networks, including EPN, CHIPS, the Image Exchange Network and the RTP network.",
                  service="Payment network infrastructure services, including the transmission and processing of ACH transactions and Real-Time Payments.",
                  business_process="ACH and RTP clearing and settlement", operational_dependency="Critical",
                  data_classification="Payment messages in transit only.", data_volume="14 million messages"),
}


@pytest.fixture
def vendor_rows():
    return {k: dict(v) for k, v in VENDOR_ROWS.items()}
