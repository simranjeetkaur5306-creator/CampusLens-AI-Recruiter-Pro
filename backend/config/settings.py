import sys
import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# backend/ folder; the .env file lives one level up (project root)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")

# True while running `python manage.py test`
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"


def env_list(name, default=""):
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]


SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY is missing. Set it in the .env file.")

DEBUG = os.getenv("DEBUG", "False") == "True"
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.postgres",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # lets logout invalidate tokens
    "corsheaders",
    # Project apps
    "core",
    "accounts",
    "candidates",
    "recruiters",
    "resumes",
    "jobs",
    "matching",
    "applications",
    "skillgap",
    "interviews",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must be above CommonMiddleware
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
                },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------- Database (PostgreSQL + pgvector) ----------
# ---------- Database (PostgreSQL + pgvector) ----------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "campuslens"),
        "USER": os.getenv("DB_USER", "campuslens_user"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

# ---------- Auth ----------
AUTH_USER_MODEL = "accounts.User"  # custom user (must be set before first migrate)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
# Django hashes passwords with PBKDF2 by default; no extra setup needed.

# ---------- Django REST Framework ----------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    # Requests per user to the endpoints that call Gemini (they use API quota); see ScopedRateThrottle
    "DEFAULT_THROTTLE_RATES": {"ai": os.getenv("AI_RATE_LIMIT", "20/hour")},
}

# ---------- Simple JWT ----------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------- CORS ----------
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)

# ---------- Internationalization ----------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# ---------- Static and media ----------
STATIC_URL = "static/"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"  # uploaded resumes (git-ignored)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------- Resume uploads ----------
RESUME_MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
RESUME_MAX_PER_CANDIDATE = 5
RESUME_ALLOWED_EXTENSIONS = (".pdf", ".docx")

# ---------- Embeddings (Phase 7) ----------
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384  # must match the model (and, in Phase 8, the pgvector column)
EMBEDDING_CHUNK_WORDS = 128
EMBEDDING_CHUNK_OVERLAP = 20
EMBEDDING_MAX_CHUNKS = 16
EMBEDDING_FAKE = TESTING  # tests use matching/fakes.py instead of downloading the real model

# ---------- Google Gemini LLM (Phase 11) ----------
# Used for interview questions and skill-gap summaries. Matching and ranking do NOT use it.
GEMINI_API_KEY = "" if TESTING else os.getenv("GEMINI_API_KEY", "")  # tests never call the real API
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "60"))
GEMINI_MAX_RETRIES = 2  # retried with exponential backoff only on rate limits, timeouts and server errors
