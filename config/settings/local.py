from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    ENV.get("DB_HOST"),
]

# CORS 설정 (개발 환경)
CORS_ALLOW_ALL_ORIGINS = True  # 개발 환경에서는 모든 요청 허용
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE"]
CORS_ALLOW_HEADERS = ["*"]


s3 = boto3.client(
    "s3",
    endpoint_url="https://kr.object.ncloudstorage.com",
    aws_access_key_id="YOUR_ACCESS_KEY_ID",
    aws_secret_access_key="YOUR_SECRET_ACCESS_KEY",
)

# CORS 설정 JSON
cors_configuration = {
    "CORSRules": [
        {
            "AllowedOrigins": ["*"],  # 필요한 경우 특정 도메인만 입력
            "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
            "AllowedHeaders": ["*"],
            "ExposeHeaders": [],
            "MaxAgeSeconds": 3000,
        }
    ]
}

# 버킷에 CORS 적용
bucket_name = "YOUR_BUCKET_NAME"
response = s3.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_configuration)
