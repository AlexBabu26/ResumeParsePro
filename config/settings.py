"""
Django settings for Parse Pro AI project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'corsheaders',
    'core',
    'accounts',
    'resumes',
    'candidates',
    'ui',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files (uploaded resumes)
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    # (6) Pagination
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    # (5) API docs
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # (Optional enhancement) Rate limiting
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        # baseline - increased for development
        'user': '3000/hour',
        'anon': '200/hour',
        # scoped throttles (set per-view via throttle_scope)
        'resumes_upload': '100/hour',
        'parse_retry': '60/hour',
        'candidate_patch': '300/hour',
        'candidates_export': '60/hour',
    },
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Parse Pro AI API',
    'DESCRIPTION': 'Resume parsing, classification, and candidate management API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Simple JWT configuration
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
}

# =============================================================================
# OPENROUTER API CONFIGURATION (Free Tier Optimized)
# =============================================================================
# API key must be set in .env (never hardcode in source)
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# Free tier models - optimized for best performance on 0 credits plan
# Models must use :free suffix for free tier access
# See: https://openrouter.ai/docs/guides/routing/model-variants/free

# Extraction model - gpt-oss-20b has MoE architecture (3.6B active params)
# for lower latency and supports structured outputs
OPENROUTER_EXTRACT_MODEL = os.getenv('OPENROUTER_EXTRACT_MODEL', 'openai/gpt-oss-20b:free')
OPENROUTER_TEMPERATURE = float(os.getenv('OPENROUTER_TEMPERATURE', '0.1'))

# Classification + summary models
OPENROUTER_CLASSIFY_MODEL = os.getenv('OPENROUTER_CLASSIFY_MODEL', 'openai/gpt-oss-20b:free')
OPENROUTER_SUMMARY_MODEL = os.getenv('OPENROUTER_SUMMARY_MODEL', 'qwen/qwen3-next-80b-a3b-instruct:free')

# Temperature settings - keep low for determinism
OPENROUTER_CLASSIFY_TEMPERATURE = float(os.getenv('OPENROUTER_CLASSIFY_TEMPERATURE', '0.1'))
OPENROUTER_SUMMARY_TEMPERATURE = float(os.getenv('OPENROUTER_SUMMARY_TEMPERATURE', '0.2'))

# Fallback models for rate limit resilience (free tier)
# When primary model is rate-limited (429), try these in order
# See: https://openrouter.ai/docs/guides/routing/model-fallbacks
# IMPORTANT: OpenRouter API limit is 3 models total (primary + fallbacks = 3 max)
# This means you can only have 2 fallback models!
OPENROUTER_FALLBACK_MODELS = [
    'nvidia/nemotron-3-nano-30b-a3b:free',    # Stable fallback
    'google/gemini-2.0-flash-exp:free',       # Fast alternative
]

# Model-specific timeouts (free models may have higher latency)
OPENROUTER_MODEL_TIMEOUTS = {
    # Free tier models
    "openai/gpt-oss-20b:free": 90,
    "qwen/qwen3-next-80b-a3b-instruct:free": 120,
    "z-ai/glm-4.5-air:free": 90,
    "nvidia/nemotron-3-nano-30b-a3b:free": 90,
    "google/gemini-2.0-flash-exp:free": 90,
    # Paid models (for future reference)
    "openai/gpt-4o-mini": 90,
    "openai/gpt-4o": 120,
    "anthropic/claude-3-haiku": 90,
    "anthropic/claude-3-sonnet": 120,
    "anthropic/claude-3-opus": 180,
    "google/gemini-pro": 90,
    "meta-llama/llama-3-8b-instruct": 60,
}
OPENROUTER_DEFAULT_TIMEOUT = 120  # Higher default for free tier

# =============================================================================
# CELERY + REDIS (Windows 11 Optimized)
# =============================================================================
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Windows 11: Use 'eventlet' for concurrent I/O-bound tasks
# The 'prefork' pool uses fork() which is not available on Windows
# Install eventlet with: pip install eventlet
# Fallback to 'solo' if eventlet has issues
#
# IMPORTANT: Do NOT use CELERY_WORKER_POOL setting!
# Use the -P flag when starting the worker instead:
#   celery -A config worker -P eventlet -c 8
# Setting CELERY_WORKER_POOL here causes warnings because patches aren't applied early enough.

# Task prefetching for better throughput
CELERY_WORKER_PREFETCH_MULTIPLIER = 2

# Task hardening settings
CELERY_TASK_TIME_LIMIT = 300  # 5 min hard limit - task will be killed after this
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 min soft limit - raises SoftTimeLimitExceeded
CELERY_TASK_ACKS_LATE = True  # Acknowledge task after completion (not before)
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Reject task if worker dies unexpectedly
CELERY_TASK_TRACK_STARTED = True  # Track when tasks start executing
CELERY_RESULT_EXPIRES = 3600  # Results expire after 1 hour

# Task routing
CELERY_TASK_ROUTES = {
    'resumes.tasks.parse_resume_parse_run': {'queue': 'resume_parse'},
}
CELERY_TASK_DEFAULT_QUEUE = 'default'

# Enable async parsing by default; allow sync override via ?sync=1
RESUME_PARSE_ASYNC = os.getenv('RESUME_PARSE_ASYNC', '1') == '1'

# -------------------------
# CORS
# -------------------------
# Allow your frontend origins. Add your deployed frontend domain(s) here.
# Use env var for flexibility across environments.
cors_origins_env = os.getenv('CORS_ALLOWED_ORIGINS', '')
if cors_origins_env.strip():
    CORS_ALLOWED_ORIGINS = [o.strip() for o in cors_origins_env.split(',') if o.strip()]
else:
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:5500',
        'http://127.0.0.1:5500',
    ]

CORS_ALLOW_CREDENTIALS = True

# If you use session auth anywhere, also set CSRF trusted origins
csrf_env = os.getenv('CSRF_TRUSTED_ORIGINS', '')
if csrf_env.strip():
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_env.split(',') if o.strip()]
else:
    CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS


# -------------------------
# LOGGING
# -------------------------
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOG_LEVEL = os.getenv('DJANGO_LOG_LEVEL', 'INFO').upper()

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'simple': {'format': '%(levelname)s %(name)s: %(message)s'},
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(name)s [%(process)d:%(thread)d] %(message)s'
        },
    },

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'app_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'app.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'celery_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'celery.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 7,
            'formatter': 'verbose',
        },
    },

    'root': {
        'handlers': ['console', 'app_file'],
        'level': LOG_LEVEL,
    },

    'loggers': {
        # Django internals
        'django': {'handlers': ['console', 'app_file'], 'level': LOG_LEVEL, 'propagate': False},
        'django.request': {'handlers': ['console', 'app_file'], 'level': LOG_LEVEL, 'propagate': False},

        # Your apps (set to INFO/DEBUG as needed)
        'resumes': {'handlers': ['console', 'app_file'], 'level': LOG_LEVEL, 'propagate': False},
        'candidates': {'handlers': ['console', 'app_file'], 'level': LOG_LEVEL, 'propagate': False},
        'accounts': {'handlers': ['console', 'app_file'], 'level': LOG_LEVEL, 'propagate': False},

        # Celery
        'celery': {'handlers': ['console', 'celery_file'], 'level': LOG_LEVEL, 'propagate': False},
    },
}

