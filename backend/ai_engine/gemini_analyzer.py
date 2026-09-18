"""Gemini adapter with structured Pydantic output and safe fallback orchestration."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
import json
from typing import Optional

from backend.ai_engine.offline import build_offline_diagnosis
from backend.ai_engine.prompts import (
    PROMPT_VERSION,
    SYSTEM_DIAGNOSIS_PROMPT,
    build_event_telemetry_prompt,
)
from backend.config import Settings, get_settings
from backend.database import DiagnosisCache
from backend.models import AIDiagnosisResult, CrashEvent, DiagnosisResponse


class GeminiAnalysisError(RuntimeError):
    """Raised when Gemini cannot return a validated diagnosis."""


class GeminiAnalyzer:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.client = None
        self.import_error: Optional[str] = None
        if not self.settings.ai_configured:
            return
        try:
            from google import genai

            self.client = genai.Client(api_key=self.settings.gemini_api_key)
        except Exception as exc:  # SDK is optional for Offline mode.
            self.import_error = str(exc)

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def analyze(self, event: CrashEvent) -> AIDiagnosisResult:
        if not self.enabled:
            raise GeminiAnalysisError(
                self.import_error or "GEMINI_API_KEY is not configured"
            )

        try:
            from google.genai import types

            response = self.client.models.generate_content(
                model=self.settings.gemini_model,
                contents=build_event_telemetry_prompt(event),
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_DIAGNOSIS_PROMPT,
                    response_mime_type="application/json",
                    response_schema=AIDiagnosisResult,
                ),
            )
            parsed = getattr(response, "parsed", None)
            if isinstance(parsed, AIDiagnosisResult):
                return parsed
            if parsed is not None:
                return AIDiagnosisResult.model_validate(parsed)

            text = getattr(response, "text", None)
            if not text:
                raise GeminiAnalysisError("Gemini returned an empty response")
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`")
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()
            return AIDiagnosisResult.model_validate(json.loads(cleaned))
        except GeminiAnalysisError:
            raise
        except Exception as exc:
            raise GeminiAnalysisError(str(exc)) from exc


class DiagnosisService:
    """Coordinates cache, Gemini, retry, timeout and deterministic fallback."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        cache: Optional[DiagnosisCache] = None,
        analyzer: Optional[GeminiAnalyzer] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.cache = cache or DiagnosisCache(self.settings.cache_db_path)
        self.analyzer = analyzer or GeminiAnalyzer(self.settings)

    def _run_with_timeout(self, event: CrashEvent) -> AIDiagnosisResult:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self.analyzer.analyze, event)
        try:
            return future.result(timeout=self.settings.ai_timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            raise GeminiAnalysisError("Gemini analysis timed out") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _gemini_with_retry(self, event: CrashEvent) -> AIDiagnosisResult:
        last_error: Optional[Exception] = None
        for _ in range(2):
            try:
                return self._run_with_timeout(event)
            except GeminiAnalysisError as exc:
                last_error = exc
        raise GeminiAnalysisError(str(last_error or "Gemini analysis failed"))

    def diagnose(self, event: CrashEvent, force_refresh: bool = False) -> DiagnosisResponse:
        model = self.settings.gemini_model if self.settings.ai_configured else None
        signature = event.signature_hash

        if self.settings.ai_configured and not force_refresh:
            cached = self.cache.get(signature, self.settings.gemini_model, PROMPT_VERSION)
            if cached:
                try:
                    diagnosis = AIDiagnosisResult.model_validate(cached["diagnosis"])
                    return DiagnosisResponse(
                        signature_hash=signature,
                        source="cache",
                        model=self.settings.gemini_model,
                        diagnosis=diagnosis,
                        warning=None,
                    )
                except Exception:
                    pass

        warning: Optional[str] = None
        if self.settings.ai_configured and self.analyzer.enabled:
            try:
                diagnosis = self._gemini_with_retry(event)
                cache_warning = None
                if not self.cache.put(
                    signature,
                    self.settings.gemini_model,
                    PROMPT_VERSION,
                    diagnosis.model_dump(),
                ):
                    cache_warning = "วิเคราะห์ด้วย Gemini สำเร็จ แต่บันทึก Cache ไม่สำเร็จ"
                return DiagnosisResponse(
                    signature_hash=signature,
                    source="gemini",
                    model=self.settings.gemini_model,
                    diagnosis=diagnosis,
                    warning=cache_warning,
                )
            except GeminiAnalysisError as exc:
                warning = f"Gemini ใช้งานไม่ได้ จึงใช้ Offline Diagnosis: {exc}"
        elif self.settings.ai_configured and self.analyzer.import_error:
            warning = (
                "พบ GEMINI_API_KEY แต่โหลด Google GenAI SDK ไม่สำเร็จ "
                "จึงใช้ Offline Diagnosis"
            )
        else:
            warning = "ยังไม่ได้ตั้งค่า GEMINI_API_KEY จึงใช้ Offline Diagnosis"

        return DiagnosisResponse(
            signature_hash=signature,
            source="offline",
            model=model,
            diagnosis=build_offline_diagnosis(event),
            generated_at=datetime.now(timezone.utc),
            warning=warning,
        )
