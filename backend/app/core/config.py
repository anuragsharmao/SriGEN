"""Configuration settings for SriGEN backend using Pydantic Settings."""

import os
from typing import List, Optional, Set
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App info
    PROJECT_NAME: str = "SriGEN - Secure Generative AI Platform"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # LLM Settings (Groq direct SDK)
    GROQ_API_KEY: Optional[str] = None
    GROQ_DEFAULT_MODEL: str = "llama-3.1-8b-instant"
    GROQ_FAST_MODEL: str = "llama-3.1-8b-instant"
    # Model used ONLY for Fact Graph extraction and Sensitivity Firewall
    # classification — the two accuracy/safety-critical stages everything
    # downstream is grounded against or gated by. Everything else (adapter
    # drafting, refine, fact-fix) stays on GROQ_DEFAULT_MODEL above, which is
    # deliberately the small/fast model: those stages run at much higher call
    # volume (many deliverables x many drafts) where Groq's free-tier daily
    # cap is the binding constraint, and lower stakes if occasionally wrong
    # (Grounding Guard + Trust Score still catch a bad draft downstream).
    # Fact Graph/Sensitivity now run at LOW call volume thanks to chunk
    # batching (see fact_graph.py), so the reasoning model's lower daily cap
    # isn't a binding constraint for them. See docs/architecture_and_hardening_plan.md §1/§4.
    GROQ_REASONING_MODEL: str = "llama-3.3-70b-versatile"

    # Gemini Developer API (google-genai SDK). Free tier via an AI Studio API
    # key, no credit card required. Model name checked against Google's own
    # lineup docs as of this writing (Sept 2026) — gemini-2.0-flash is already
    # shut down and gemini-2.5-* is scheduled to shut down 16 Oct 2026, so
    # gemini-3.1-flash-lite (GA/stable since May 2026, no shutdown scheduled)
    # is the safer default. Re-verify against
    # https://ai.google.dev/gemini-api/docs/models before a long-lived deploy —
    # Google's free-tier lineup moves fast.
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_DEFAULT_MODEL: str = "gemini-3.1-flash-lite"
    GEMINI_REQUESTS_PER_MINUTE: int = 12
    # Used for the same accuracy-critical stages GROQ_REASONING_MODEL is used
    # for (Fact Graph / Sensitivity / Source Understanding) when the Gemini
    # backend is active — see the REASONING_MODEL property below. Same model
    # as GEMINI_DEFAULT_MODEL for now; split it out (e.g. to gemini-3-flash-
    # preview) if/when you want a stronger model on just those stages.
    GEMINI_REASONING_MODEL: str = "gemini-3.1-flash-lite"

    # Source Understanding (merged Fact Graph + Sensitivity Classification —
    # see app/services/source_understanding.py). Both jobs now read the same
    # chunk/batch of source text in ONE structured-output call instead of two
    # separate chunked passes. Chunk/batch size is kept small and, for now,
    # equal to each other (one chunk per call, no re-batching) because this
    # is running against Groq's FREE tier: smaller requests are safer against
    # a free-tier reasoning model's per-request token limits, at the cost of
    # more (but still fully parallel, via asyncio.gather) calls than a paid
    # tier would need. Once off the free tier, raise
    # SOURCE_UNDERSTANDING_BATCH_MAX_CHARS well above SOURCE_CHUNK_TARGET_CHARS
    # to fold several chunks into fewer calls again (same mechanism
    # fact_graph.py's original BATCH_MAX_CHARS used).
    SOURCE_CHUNK_TARGET_CHARS: int = 3000
    SOURCE_CHUNK_OVERLAP_CHARS: int = 250
    SOURCE_UNDERSTANDING_BATCH_MAX_CHARS: int = 3000
    # Multimodal ingestion models (overridable via env; verify against
    # https://console.groq.com/docs/vision and /docs/speech-to-text before relying
    # on these defaults long-term, since Groq's available model list changes).
    GROQ_VISION_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    GROQ_TRANSCRIBE_MODEL: str = "whisper-large-v3-turbo"

    # Multimodal ingestion limits
    MAX_UPLOAD_SIZE_MB: int = 25

    # Max characters of raw source text included verbatim in the generation
    # prompt (app/adapters/base.py::_build_context_prompt). Previously
    # hardcoded to 4000 with no config surface and no visibility when a
    # longer document got silently cut. The Fact Graph itself is always
    # built from the FULL source text (app/services/fact_graph.py) regardless
    # of this limit, so no fact is lost — this only bounds how much raw
    # phrasing/context an adapter sees directly. Raised well above the old
    # 4000: Groq's Llama 3.3 70B has a 128K-token context window, so this
    # costs little against that budget even at several times this size.
    MAX_GENERATION_CONTEXT_CHARS: int = 20000

    # Database
    DATABASE_URL: str = "sqlite:///./srigen.db"

    # Provenance Ledger
    OPERATOR_ID: str = "operator_sec_01"
    LEDGER_GENESIS_HASH: str = "0000000000000000000000000000000000000000000000000000000000000000"

    # Security Firewall: Built-in sensitive marker patterns & classified regexes (structural only)
    SENSITIVE_PATTERNS: dict = {
        "LOCATION": [
            r"\b(?:Forward Operating Base [A-Z0-9\-]+|Sector-[0-9]+|Site-[A-Z0-9]+|Grid Ref [0-9A-Z]+|Station [A-Z0-9]+|Post [0-9]+)\b",
            r"\b(?:Lat\s*-?\d+\.\d+,\s*Long\s*-?\d+\.\d+|\b\d{1,2}°\d{1,2}'[NS]\s+\d{1,3}°\d{1,2}'[EW]\b)\b",
        ],
        "UNIT_NAME": [
            r"\b(?:Cyber Command Division [0-9]+|NTRO-[A-Z0-9]+|Task Force [0-9A-Z]+|Special Operations Wing|Signals Directorate)\b",
            r"\b(?:Unit [0-9]{3,4}|Detachment [A-Z0-9]+)\b"
        ],
        "CLASSIFIED_ASSET": [
            r"\b(?:SAT-COMM-[0-9]+|PROJECT-[A-Z0-9]+|INS-[A-Z0-9]+|RADAR-ARRAY-[0-9]+)\b",
            r"\b(?:Operation [A-Z][a-zA-Z0-9]+|Vault-[0-9]+)\b"
        ],
        "PERSON": [
            r"\b(?:Director General [A-Z][a-z]+ [A-Z][a-z]+|Brigadier [A-Z][a-z]+|Col\. [A-Z][a-z]+|Agent [0-9A-Z]+)\b"
        ],
        "IP_ADDRESS": [
            r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})\b"
        ]
    }

    # Document furniture and stopwords that should never be treated as named entities
    ENTITY_BOILERPLATE: Set[str] = {
        "for immediate release",
        "frequently asked questions",
        "executive summary",
        "situation report",
        "key highlights",
        "recommended actions",
        "background",
        "current status",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
        "immediate release",
        "operational", "immediate", "reaffirms",
    }

    # Generic, category-appropriate phrases for public-facing exports, keyed by
    # (category, sensitivity_tier) so a withheld "contextual" item reads
    # slightly less generic than a withheld "sensitive" one. CLASSIFIED_ASSET
    # and IP_ADDRESS are always "sensitive" (see _RESTRICTED_CATEGORIES in
    # orchestrator.py), so they only need that one bucket. If an analyst
    # manually withholds a "routine" item, or a tier has no dedicated phrase
    # set, _generic_phrase_for() falls back to the "sensitive" bucket, then to
    # a hardcoded default — never a KeyError.
    GENERIC_PLACEHOLDER_PHRASES: dict = {
        "LOCATION": {
            "contextual": {
                "en": ["an internal facility", "a company site", "a regional office"],
                "hi": ["एक आंतरिक सुविधा", "एक कंपनी स्थल", "एक क्षेत्रीय कार्यालय"],
            },
            "sensitive": {
                "en": ["an affected location", "a regional site", "the affected area"],
                "hi": ["एक प्रभावित स्थान", "एक क्षेत्रीय स्थल", "प्रभावित क्षेत्र"],
            },
        },
        "UNIT_NAME": {
            "contextual": {
                "en": ["an internal team", "a designated group", "an operational unit"],
                "hi": ["एक आंतरिक टीम", "एक निर्दिष्ट समूह", "एक परिचालन इकाई"],
            },
            "sensitive": {
                "en": ["the responding unit", "the designated unit", "the operational team"],
                "hi": ["प्रतिक्रिया इकाई", "निर्दिष्ट इकाई", "परिचालन दल"],
            },
        },
        "CLASSIFIED_ASSET": {
            "sensitive": {
                "en": ["the protected asset", "operational infrastructure"],
                "hi": ["संरक्षित संपत्ति", "परिचालन अवसंरचना"],
            },
        },
        "PERSON": {
            "contextual": {
                "en": ["a staff member", "an internal contact", "a team member"],
                "hi": ["एक कर्मचारी", "एक आंतरिक संपर्क", "एक टीम सदस्य"],
            },
            "sensitive": {
                "en": ["the individual", "the unnamed individual", "the person involved"],
                "hi": ["संबंधित व्यक्ति", "नामोल्लेख रहित व्यक्ति", "संबद्ध व्यक्ति"],
            },
        },
        "IP_ADDRESS": {
            "sensitive": {
                "en": ["a network endpoint"],
                "hi": ["एक नेटवर्क एंडपॉइंट"],
            },
        },
        "OTHER_SENSITIVE": {
            "contextual": {
                "en": ["an internal detail"],
                "hi": ["एक आंतरिक विवरण"],
            },
            "sensitive": {
                "en": ["an operational detail"],
                "hi": ["एक परिचालन विवरण"],
            },
        },
    }

    # CORS: explicit allowlist only, read from a comma-separated env string.
    # Defaults to localhost dev origins only — never "*", since allow_credentials
    # is True once auth tokens are in play (a "*" + credentials combination is
    # rejected by browsers anyway, and is a real cross-origin risk otherwise).
    CORS_ORIGINS_RAW: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Auth (default credential-based implementation — see app/services/auth.py).
    # Bootstrap account created on first startup ONLY if no operator exists yet;
    # leave unset in any shared/production environment once real accounts exist.
    OPERATOR_BOOTSTRAP_USERNAME: Optional[str] = None
    OPERATOR_BOOTSTRAP_PASSWORD: Optional[str] = None

    # Pluggable LLM backend selection (item 4). "groq" and "gemini" are both
    # implemented; the LLMBackend interface in app/core/llm_client.py exists
    # so a self-hosted/VPC-scoped backend can be added later without touching
    # orchestrator/adapter/service code.
    #
    # LLM_BACKEND is the primary backend every call is tried against first.
    # LLM_FALLBACK_BACKEND, if set to a different backend name, is tried
    # automatically whenever the primary raises LLMUnavailableError (missing/
    # invalid key, rate limit exhausted, 5xx, connection failure) — see
    # FallbackBackend in llm_client.py. Set LLM_FALLBACK_BACKEND to "" or the
    # same value as LLM_BACKEND to disable fallback entirely.
    LLM_BACKEND: str = "gemini"
    LLM_FALLBACK_BACKEND: Optional[str] = "groq"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def REASONING_MODEL(self) -> str:
        """The reasoning-tier model name for whichever backend LLM_BACKEND
        currently points at — used by the accuracy-critical stages (Fact
        Graph, Sensitivity Firewall, Source Understanding) instead of each of
        those call sites hardcoding `settings.GROQ_REASONING_MODEL` directly.

        Those call sites used to pass the Groq model name explicitly to
        `llm_client.structured_completion(model=...)`, which OVERRIDES
        whatever backend-internal default `target_model = model or
        settings.GROQ_DEFAULT_MODEL` would otherwise pick — so switching
        LLM_BACKEND alone did nothing for them; they'd keep sending a Groq
        model name straight to whichever backend was actually active and
        fail every call. This property is what they should pass instead.
        """
        backend = (self.LLM_BACKEND or "gemini").strip().lower()
        if backend == "groq":
            return self.GROQ_REASONING_MODEL
        if backend == "gemini":
            return self.GEMINI_REASONING_MODEL
        return self.GROQ_REASONING_MODEL

    @property
    def CORS_ORIGINS(self) -> List[str]:
        origins = [o.strip() for o in self.CORS_ORIGINS_RAW.split(",") if o.strip()]
        if "*" in origins:
            # Never combine a wildcard with allow_credentials=True (main.py always
            # sets allow_credentials=True once auth exists) — drop it rather than
            # silently allow every origin to send credentialed requests.
            origins = [o for o in origins if o != "*"]
        return origins


settings = Settings()
