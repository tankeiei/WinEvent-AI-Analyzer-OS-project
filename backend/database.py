"""Small SQLite cache for validated Gemini diagnoses."""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import sqlite3
from pathlib import Path
from typing import Iterator, Optional

from backend.config import get_settings


class DiagnosisCache:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path or get_settings().cache_db_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(self.db_path), timeout=3)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout=3000")
            yield connection
            connection.commit()
        finally:
            connection.close()

    def ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS diagnosis_cache (
                    signature_hash TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    diagnosis_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (signature_hash, model, prompt_version)
                )
                """
            )

    def is_ready(self) -> bool:
        try:
            self.ensure_schema()
            return True
        except (OSError, sqlite3.Error):
            return False

    def get(
        self, signature_hash: str, model: str, prompt_version: str
    ) -> Optional[dict]:
        try:
            self.ensure_schema()
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT diagnosis_json, created_at
                    FROM diagnosis_cache
                    WHERE signature_hash = ? AND model = ? AND prompt_version = ?
                    """,
                    (signature_hash, model, prompt_version),
                ).fetchone()
            if row is None:
                return None
            return {
                "diagnosis": json.loads(row["diagnosis_json"]),
                "created_at": row["created_at"],
            }
        except (OSError, sqlite3.Error, json.JSONDecodeError, TypeError):
            return None

    def put(
        self,
        signature_hash: str,
        model: str,
        prompt_version: str,
        diagnosis: dict,
    ) -> bool:
        try:
            self.ensure_schema()
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO diagnosis_cache
                    (signature_hash, model, prompt_version, diagnosis_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        signature_hash,
                        model,
                        prompt_version,
                        json.dumps(diagnosis, ensure_ascii=False),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
            return True
        except (OSError, sqlite3.Error, TypeError, ValueError):
            return False
