"""Loads, validates and versions the methodology configuration."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import MethodologyVersion

REQUIRED_SECTIONS = ["criticality", "assessment_depth", "source_reliability", "evidence_strength",
                     "ai_classification", "risk", "recommendations"]


class MethodologyError(ValueError):
    pass


@dataclass(frozen=True)
class Methodology:
    id: str | None
    version: str
    content_hash: str
    config: dict[str, Any]

    @property
    def label(self) -> str:
        return f"{self.version}+{self.content_hash[:8]}"

    def __getitem__(self, key: str) -> Any:
        return self.config[key]


def _check_weights(section: str, weights: dict[str, float]) -> None:
    total = round(sum(float(v) for v in weights.values()), 6)
    if abs(total - 1.0) > 1e-6:
        raise MethodologyError(f"{section} weights must sum to 1.0 (got {total})")
    if any(float(v) < 0 for v in weights.values()):
        raise MethodologyError(f"{section} weights must be non-negative")


def validate_config(cfg: dict[str, Any]) -> None:
    missing = [s for s in REQUIRED_SECTIONS if s not in cfg]
    if missing:
        raise MethodologyError(f"missing sections: {missing}")
    _check_weights("criticality", cfg["criticality"]["weights"])
    _check_weights("evidence_strength", cfg["evidence_strength"]["weights"])
    _check_weights("risk", cfg["risk"]["weights"])
    for section, key in (("criticality", "thresholds"), ("risk", "thresholds")):
        vals = list(cfg[section][key].values())
        if vals != sorted(vals, reverse=True):
            raise MethodologyError(f"{section}.{key} must be listed from highest to lowest")
    tiers = cfg["assessment_depth"]["tiers"]
    for t in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        if t not in tiers:
            raise MethodologyError(f"assessment_depth tier {t} missing")


def parse_yaml(text: str) -> dict[str, Any]:
    try:
        cfg = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise MethodologyError(f"invalid YAML: {exc}") from exc
    if not isinstance(cfg, dict):
        raise MethodologyError("methodology must be a mapping")
    validate_config(cfg)
    return cfg


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_from_file() -> tuple[str, dict[str, Any]]:
    text = get_settings().methodology_path.read_text(encoding="utf-8")
    return text, parse_yaml(text)


def file_methodology() -> Methodology:
    """Methodology straight from the YAML file (used by tests and as a fallback)."""
    text, cfg = load_from_file()
    return Methodology(id=None, version=str(cfg["version"]), content_hash=_hash(text), config=cfg)


def register(db: Session, text: str, created_by: str = "system", note: str | None = None,
             activate: bool = True) -> MethodologyVersion:
    cfg = parse_yaml(text)
    h = _hash(text)
    existing = db.scalar(select(MethodologyVersion).where(MethodologyVersion.content_hash == h))
    row = existing or MethodologyVersion(version=str(cfg["version"]), content_hash=h, config=cfg,
                                         yaml_text=text, created_by=created_by, note=note)
    if not existing:
        db.add(row)
    if activate:
        for other in db.scalars(select(MethodologyVersion).where(MethodologyVersion.is_active.is_(True))):
            other.is_active = False
        row.is_active = True
    db.flush()
    return row


def sync_file_version(db: Session) -> MethodologyVersion:
    """Register methodology.yaml if its content is new. A changed file on disk
    becomes the active version (recorded with a note); unchanged files leave an
    analyst-activated version in place."""
    text, _ = load_from_file()
    h = _hash(text)
    if db.scalar(select(MethodologyVersion).where(MethodologyVersion.content_hash == h)):
        return ensure_active(db)
    return register(db, text, note="methodology.yaml changed on disk; registered at startup")


def ensure_active(db: Session) -> MethodologyVersion:
    active = db.scalar(select(MethodologyVersion).where(MethodologyVersion.is_active.is_(True)))
    if active:
        return active
    text, _ = load_from_file()
    return register(db, text, note="Initial methodology loaded from methodology.yaml")


def active_methodology(db: Session) -> Methodology:
    row = ensure_active(db)
    return Methodology(id=row.id, version=row.version, content_hash=row.content_hash, config=row.config)


def methodology_by_id(db: Session, mid: str) -> Methodology:
    row = db.get(MethodologyVersion, mid)
    if not row:
        raise MethodologyError("unknown methodology version")
    return Methodology(id=row.id, version=row.version, content_hash=row.content_hash, config=row.config)
