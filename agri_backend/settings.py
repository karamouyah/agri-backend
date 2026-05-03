"""
File responsibility: Configures Django, REST Framework, PostgreSQL, authentication, CORS, security, and static files.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

INSECURE_SECRET_KEY = "insecure-dev-only-secret-key-change-me"
# Allow all hosts by default — restrict via DJANGO_ALLOWED_HOSTS env var in production.
DEFAULT_ALLOWED_HOSTS = "*"
# Local dev CORS origins. Override in production via CORS_ALLOWED_ORIGINS env var.
DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
# CSRF trusted origins — must include the Railway backend HTTPS domain for POST to work.
DEFAULT_CSRF_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,https://agri-app-production-4d98.up.railway.app"


def get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def get_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_database_url_config(database_url: str) -> dict:
    parsed = urlparse(database_url)
    engine_map = {
        "postgres": "django.db.backends.postgresql",
        "postgresql": "django.db.backends.postgresql",
    }
    engine = engine_map.get(parsed.scheme)

    if not engine:
        raise ImproperlyConfigured(
            "DATABASE_URL must use a supported PostgreSQL scheme such as postgres:// or postgresql://."
        )

    database = {
        "ENGINE": engine,
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
        "CONN_MAX_AGE": get_int("DB_CONN_MAX_AGE", 60),
        "CONN_HEALTH_CHECKS": get_bool("DB_CONN_HEALTH_CHECKS", True),
    }

    options = dict(parse_qsl(parsed.query, keep_blank_values=False))
    if options:
        database["OPTIONS"] = options

    return database


def get_database_config() -> dict:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return get_database_url_config(database_url)

    engine = os.getenv("DB_ENGINE", "django.db.backends.postgresql").strip()

    if engine == "django.db.backends.sqlite3":
        return {
            "ENGINE": engine,
            "NAME": os.getenv("DB_NAME", BASE_DIR / "db.sqlite3"),
        }

    database = {
        "ENGINE": engine,
        "NAME": os.getenv("DB_NAME", "agri_app"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": get_int("DB_CONN_MAX_AGE", 60),
        "CONN_HEALTH_CHECKS": get_bool("DB_CONN_HEALTH_CHECKS", True),
    }

    sslmode = os.getenv("DB_SSLMODE")
    if sslmode:
        database["OPTIONS"] = {"sslmode": sslmode}

    return database


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", INSECURE_SECRET_KEY)
DEBUG = get_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = get_list("DJANGO_ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS)

if not DEBUG and SECRET_KEY == INSECURE_SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set to a secure value when DJANGO_DEBUG is False.")

if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set when DJANGO_DEBUG is False.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "apps.locations",
    "apps.users",
    "apps.catalog",
    "apps.orders",
    "apps.logistics",
    "apps.reports",
    "apps.documents",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "agri_backend.urls"

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

WSGI_APPLICATION = "agri_backend.wsgi.application"
ASGI_APPLICATION = "agri_backend.asgi.application"

DATABASES = {
    "default": get_database_config()
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

# Security: keep browser and proxy hardening enabled in production.
SECURE_SSL_REDIRECT = get_bool("SECURE_SSL_REDIRECT", not DEBUG)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = get_bool("USE_X_FORWARDED_HOST", not DEBUG)
SECURE_HSTS_SECONDS = get_int("SECURE_HSTS_SECONDS", 0 if DEBUG else 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = get_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", not DEBUG)
SECURE_HSTS_PRELOAD = get_bool("SECURE_HSTS_PRELOAD", False)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

CORS_ALLOWED_ORIGINS = get_list(
    "CORS_ALLOWED_ORIGINS",
    DEFAULT_CORS_ORIGINS,
)
CSRF_TRUSTED_ORIGINS = get_list(
    "CSRF_TRUSTED_ORIGINS",
    DEFAULT_CSRF_ORIGINS,
)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "50/hour",
        "user": "300/hour",
        "auth": "10/minute",
    },
}

access_minutes = get_int("JWT_ACCESS_MINUTES", 30)
refresh_days = get_int("JWT_REFRESH_DAYS", 7)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=access_minutes),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=refresh_days),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}
