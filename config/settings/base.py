"""
Django settings for config project.

Generated by 'django-admin startproject' using Django 5.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

import sys
from datetime import timedelta
from pathlib import Path

# import boto3
from dotenv import dotenv_values

# from storages.backends import s3

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# .env 파일 로드
ENV = dotenv_values(".env")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = ENV.get("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "https://toonchu-fe.vercel.app/",
    "toonchu.com",
    ENV.get("DB_HOST"),
]

# Application definition
CUSTOM_APPS = [
    "users",
    "webtoons",
    "bookmark",
    "corsheaders",
]

SYSTEM_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "storages",
]

INSTALLED_APPS = CUSTOM_APPS + SYSTEM_APPS + THIRD_PARTY_APPS  # + ['corsheaders']

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
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
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": ENV.get("DB_ENGINE"),
        "NAME": ENV.get("DB_NAME"),
        "USER": ENV.get("DB_USER"),
        "PASSWORD": ENV.get("DB_PASSWORD"),
        "HOST": ENV.get("DB_HOST"),
        "PORT": ENV.get("DB_PORT"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Swagger settings
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # # JWT 토큰 활성화 후 적용
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}

# Swagger settings
SPECTACULAR_SETTINGS = {
    "TITLE": "toonchu",
    "DESCRIPTION": "toonchu",
    "VERSION": "1.0.0",
    "COMPONENT_SPLIT_REQUEST": True,  # 요청과 응답 스키마 분리
    "SERVE_INCLUDE_SCHEMA": False,  # 스키마 엔드포인트를 포함하지 않도록 설정
}  # '/api/schema/' 숨김처리

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "ko-kr"

TIME_ZONE = "Asia/Seoul"

USE_I18N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files
# MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom user model
AUTH_USER_MODEL = "users.CustomUser"

SITE_ID = 1

LOGIN_REDIRECT_URL = "/"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
}

# OAuth settings
KAKAO_CLIENT_ID = ENV.get("KAKAO_REST_API_KEY")  # 변경된 부분
KAKAO_CLIENT_SECRET = ENV.get("KAKAO_SECRET")
KAKAO_CALLBACK_URL = ENV.get("KAKAO_REDIRECT_URI")

GOOGLE_CLIENT_ID = ENV.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = ENV.get("GOOGLE_SECRET")
GOOGLE_CALLBACK_URL = ENV.get("GOOGLE_REDIRECT_URI")

NAVER_CLIENT_ID = ENV.get("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = ENV.get("NAVER_SECRET")
NAVER_CALLBACK_URL = ENV.get("NAVER_REDIRECT_URI")


# http로 변경 (또는 .env 파일의 URL들을 https로 변경)
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"


CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    # "http://localhost:3000",
    # "https://toonchu-fe.vercel.app",
    "https://toonchu.com"
]
CORS_ALLOW_CREDENTIALS = True  # 인증정보 포함 허용


GOOGLE_OAUTH2_SCOPE = ["email", "profile"]  # 새로운 설정 추가


# FRONTEND_URL = "https://toonchu-fe.vercel.app/"

# s3 = boto3.client('s3', aws_access_key_id=ENV.get("ACCESS_KEY"), aws_secret_access_key=ENV.get("SECRET_KEY"))
# response = s3.list_buckets()
# buckets = [bucket['NAME'] for bucket in response['Buckets']]
#
# # 파일 업로드
# s3.upload_file('myfile-txt', 'my_bucket', 'myfile.txt')
# # 파일 다운로드
# s3.download_file('my_bucket', 'myfile.txt', 'myfile_downloaded.txt')
# # 파일 삭제
# s3.delete_file(Bucket='my_bucket', Key='myfile.txt')

# s3 = boto3.client('s3', endpoint_url='https://your_endpoint_url', aws_access_key_id='YOUR_ACCESS_KEY', aws_secret_access_key='YOUR_SECRET_KEY')
#
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

NCP_ACCESS_KEY_ID = ENV.get("NCP_ACCESS_KEY_ID")
NCP_SECRET_ACCESS_KEY = ENV.get("NCP_SECRET_ACCESS_KEY")
NCP_STORAGE_BUCKET_NAME = ENV.get("NCP_STORAGE_BUCKET_NAME")
NCP_S3_ENDPOINT_URL = ENV.get("NCP_S3_ENDPOINT_URL")
# AWS_QUERYSTRING_AUTH = False  # URL에 인증 정보를 포함하지 않음
# AWS_DEFAULT_ACL = None
# AWS_S3_FILE_OVERWRITE = False
# AWS_LOCATION = "users/profile"  # 업로드될 디렉토리 지정 (예: 프로필 이미지용)


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            "datefmt": "%d/%b/%Y %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "console.info": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": True,
        },
        "console.error": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": True,
        },
        "logger.info": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "logger.warning": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False,
        },
        "logger.error": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

NCP_ACCESS_KEY = ENV.get("NCP_ACCESS_KEY")
NCP_SECRET_KEY = ENV.get("NCP_SECRET_KEY")
NCP_OBJECT_STORAGE_ENDPOINT = ENV.get("IMAGE_BUCKET_ENDPOINT")
BUCKET_NAME = ENV.get("BUCKET_NAME")
