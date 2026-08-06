"""Filesystem-backed store for generated report documents.

The platform is read-only (no INSERT/UPDATE/DELETE against the database), so
generated reports live in a lightweight JSON cache on disk. Each document is
stored as ``<report_id>.json`` under a configured directory (default: the
platform temp directory). The store is safe to re-create per request because
it only resolves the same on-disk location.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.models.domain import ReportSummary
from app.models.report import ReportDocument


class ReportStore:
    """JSON file cache for :class:`ReportDocument` instances."""

    def __init__(self, storage_dir: str = "") -> None:
        base = Path(storage_dir) if storage_dir else Path(tempfile.gettempdir())
        self._dir = base / "bip_reports"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, report_id: str) -> Path:
        return self._dir / f"{report_id}.json"

    def save(self, document: ReportDocument) -> None:
        """Persist a document atomically (write temp file, then rename)."""
        path = self._path(document.id)
        tmp = self._dir / f".{document.id}.tmp"
        tmp.write_text(document.model_dump_json(), encoding="utf-8")
        tmp.replace(path)

    def get(self, report_id: str) -> Optional[ReportDocument]:
        """Load one document by id, or ``None`` when absent."""
        path = self._path(report_id)
        if not path.exists():
            return None
        try:
            return ReportDocument.model_validate_json(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None

    def list_documents(self) -> List[ReportDocument]:
        """Return all stored documents (newest first)."""
        documents: List[ReportDocument] = []
        for path in sorted(self._dir.glob("*.json")):
            document = self.get(path.stem)
            if document is not None:
                documents.append(document)
        documents.sort(key=lambda d: d.generated_at, reverse=True)
        return documents

    def list_summaries(
        self,
        *,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[ReportSummary]:
        """Return stored report summaries, optionally narrowed by generation time."""
        summaries: List[ReportSummary] = []
        for document in self.list_documents():
            if date_from is not None and document.generated_at < date_from:
                continue
            if date_to is not None and document.generated_at > date_to:
                continue
            summaries.append(document.to_summary())
        return summaries

    def get_summary(self, report_id: str) -> Optional[ReportSummary]:
        document = self.get(report_id)
        return document.to_summary() if document is not None else None
