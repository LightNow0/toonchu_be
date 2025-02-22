import datetime
import logging
import uuid

import boto3
import requests
from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import InMemoryUploadedFile, UploadedFile
from django.db import IntegrityError  # connection 제거
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions, serializers, status
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from users.serializers import (
    LogoutSerializer,
    NicknameCheckSerializer,
    UserProfileSerializer,
)

from .utils import RendomNickName

User = get_user_model()

logger = logging.getLogger(__name__)


class SocialLoginView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, provider):
        logger.debug(f"소셜로그인 요청 시 로그: {provider}")

        # 프론트에서 받은 인가 코드
        auth_code = request.data.get("code")
        if not auth_code:
            return Response(
                {"error": "Authorization code is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.debug(f"프론트에서 전달한 인가코드: {auth_code}")

        # 인가 코드를 access_token으로 변환
        access_token = self.get_access_token(provider, auth_code)
        if not access_token:
            return Response(
                {"error": "Failed to retrieve access token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        logger.debug(f"소셜로그인 API로 받은 액세스토큰: {access_token}")

        # access_token을 사용하여 사용자 정보 가져오기
        user_info = self.get_social_user_info(provider, access_token)
        if not user_info:
            return Response(
                {"error": "Invalid social token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # logger.debug(f"액세스토큰 이용 사용자 정보: {user_info}")
        #
        # # 닉네임이 없는 경우 랜덤 닉네임 생성
        # nick_name = user_info.get("nick_name")
        # is_hidden = False
        # if not nick_name:  # 닉네임이 None 또는 빈 값이면
        #     nick_name, is_hidden = RendomNickName()  # 랜덤 닉네임과 히든 여부 반환

        # 사용자 정보로 DB 조회 및 저장
        try:
            user, created = User.objects.get_or_create(
                email=user_info["email"],
                provider=provider,
                defaults={
                    # "nick_name": nick_name,  # 닉네임 저장
                    "profile_img": user_info.get("profile_image"),
                    "is_hidden": is_hidden,  # 히든 여부 저장
                },
            )
            #
            # # 닉네임 변경 시 기존 닉네임이 히든이면 is_hidden을 False로 변경
            # if not created and user.is_hidden:
            #     user.is_hidden = False
            #     user.save()

        except IntegrityError as e:
            logger.error(f"IntegrityError occurred: {str(e)}")
            return Response(
                {"error": "User already exists or database constraint violated"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        #  로그인 시 user.is_active가 False or 0 이면 로그인 불가 처리
        if not user.is_active:
            return Response(
                {"error": "Your account is inactive. Please contact support."},
                status=status.HTTP_400_BAD_REQUEST,  # 403 상태 코드 반환
            )

        # JWT 토큰 생성
        token = RefreshToken.for_user(user)

        # Access Token만 반환
        return Response(
            {
                "access_token": str(token.access_token),
                "refresh_token": str(token),
                "user": {
                    "id": user.id,
                    "nick_name": user.nick_name,
                    "email": user.email,
                    "profile_image": user.profile_img.url if user.profile_img else "",
                    "provider": user.provider,
                },
            },
            status=status.HTTP_200_OK,
        )

    def get_access_token(self, provider, auth_code):
        # 인가 코드로 access token 요청
        if provider == "kakao":
            return self.get_kakao_access_token(auth_code)
        elif provider == "naver":
            return self.get_naver_access_token(auth_code)
        elif provider == "google":
            return self.get_google_access_token(auth_code)
        return None

    def get_kakao_access_token(self, auth_code):
        # 카카오 인가 코드 → Access Token 변환
        url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.KAKAO_CLIENT_ID,
            "redirect_uri": settings.KAKAO_CALLBACK_URL,
            "code": auth_code,
            "client_secret": settings.KAKAO_CLIENT_SECRET,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            logger.debug(f"Kakao Token Request: {data}")  # 요청 데이터 로그
            response = requests.post(url, data=data, headers=headers)
            logger.debug(
                f"Kakao access token response: {response.status_code} {response.text}"
            )
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                logger.error(
                    f"Kakao access token failed: {response.status_code} - {response.text}"
                )
        except Exception as e:
            logger.error(f"Error occurred while getting Kakao access token: {str(e)}")
        return None

    def get_naver_access_token(self, auth_code):
        # 네이버 인가 코드 → Access Token 변환
        url = "https://nid.naver.com/oauth2.0/token"
        params = {
            "grant_type": "authorization_code",
            "client_id": settings.NAVER_CLIENT_ID,
            "client_secret": settings.NAVER_CLIENT_SECRET,
            "code": auth_code,
            "state": "random_state_string",  # 보안 강화를 위해 사용
        }
        try:
            response = requests.get(url, params=params)
            logger.debug(
                f"Naver access token response: {response.status_code} {response.text}"
            )
            if response.status_code == 200:
                return response.json().get("access_token")
        except Exception as e:
            logger.error(f"Error occurred while getting Naver access token: {str(e)}")
        return None

    def get_google_access_token(self, auth_code):
        # 구글 인가 코드 → Access Token 변환
        url = "https://oauth2.googleapis.com/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_CALLBACK_URL,
            "code": auth_code,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            response = requests.post(url, data=data, headers=headers)
            logger.debug(
                f"Google access token response: {response.status_code} {response.text}"
            )
            if response.status_code == 200:
                return response.json().get("access_token")
        except Exception as e:
            logger.error(f"Error occurred while getting Google access token: {str(e)}")
        return None

    def get_social_user_info(self, provider, access_token):
        logger.debug(f"Getting user info for provider: {provider}")

        # access_token -> 소셜 사용자 정보 가져오기
        try:
            if provider == "kakao":
                url = "https://kapi.kakao.com/v2/user/me"
                headers = {"Authorization": f"Bearer {access_token}"}
                response = requests.get(url, headers=headers)
                logger.debug(
                    f"Kakao API response: {response.status_code} {response.text}"
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "email": data["kakao_account"].get("email"),
                        "nick_name": data["properties"].get("nick_name"),
                        "profile_image": data["properties"].get("profile_image"),
                    }

            elif provider == "naver":
                url = "https://openapi.naver.com/v1/nid/me"
                headers = {"Authorization": f"Bearer {access_token}"}
                response = requests.get(url, headers=headers)
                logger.debug(
                    f"Naver API response: {response.status_code} {response.text}"
                )
                if response.status_code == 200:
                    data = response.json()["response"]
                    return {
                        "email": data.get("email"),
                        "nick_name": data.get("nick_name"),
                        "profile_image": data.get("profile_image"),
                    }
            elif provider == "google":
                url = "https://www.googleapis.com/oauth2/v3/userinfo"
                headers = {"Authorization": f"Bearer {access_token}"}
                response = requests.get(url, headers=headers)
                logger.debug(
                    f"Google API response: {response.status_code} {response.text}"
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "email": data.get("email"),
                        "nick_name": data.get("name"),
                        "profile_image": data.get("picture"),
                    }
        except Exception as e:
            logger.error(
                f"Error occurred while fetching user info from {provider}: {str(e)}"
            )

        return None


class TokenRefreshView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                {"error": "Bearer token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        refresh_token = auth_header.split(" ")[1]

        try:
            # RefreshToken 검증
            token = RefreshToken(refresh_token)
            user_id = token.payload.get("user_id")

            if not user_id:
                return Response(
                    {"error": "Invalid refresh token"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 사용자 조회
            user = User.objects.get(id=user_id)

            # 새로운 access token 생성
            new_access_token = str(AccessToken.for_user(user))

            return Response(
                {"access_token": new_access_token}, status=status.HTTP_200_OK
            )

        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except InvalidToken:
            return Response(
                {"error": "Invalid refresh token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except TokenError:
            return Response(
                {"error": "Expired refresh token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# class LogoutView(APIView):
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]
#
#     def post(self, request):
#         print(request.data)
#         try:
#             refresh_token = request.data.get("refresh_token")
#
#             if refresh_token:
#                 serializer = LogoutSerializer(data=request.data)
#                 if serializer.is_valid():
#                     token = serializer.data.get("refresh_token")
#                     token.blacklist()
#                     logger.debug(f"Token blacklist: {token}")
#
#                 return Response(
#                     {"message": "로그아웃 되었습니다."}, status=status.HTTP_200_OK
#                 )
#             else:
#                 return Response(
#                     {"error": "리프레시 토큰이 제공되지 않았습니다."},
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


CustomUser = get_user_model()


class LogoutView(APIView):
    # authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]
    serializer_class = LogoutSerializer

    def post(self, request):
        # raise Exception("1123")
        refresh_token = request.data.get("refresh_token")
        logger.info(f"Received refresh_token:{refresh_token}")
        logger.info(f"User ID: {request.user.id}")

        if not refresh_token:
            return Response(
                {"error": "리프레시 토큰이 제공되지 않았습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            logger.info("RefreshToken 객체 생성 성공!")
            token.blacklist()
            logger.info("RefreshToken 블랙리스트 추가 성공!")

            # 블랙리스트 등록 여부 직접 확인
            # is_blacklisted = BlacklistedToken.objects.filter(token=str(token)).exists()
            # if is_blacklisted:
            #     logger.info("토큰이 블랙리스트에 정상적으로 추가되었습니다.")
            # else:
            #     logger.warning("토큰이 블랙리스트에 추가되지 않았습니다!")

            return Response(
                {"message": "로그아웃 되었습니다.", "user_id": request.user.id},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)


class UserProfileView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserProfileSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get(self):
        return self.request.user

    def ncp_image(self, img_url: str | None) -> bool:
        if img_url is None:
            return False
        return settings.AWS_STORAGE_BUCKET_NAME in img_url

    def upload_ncp(self, img_file: UploadedFile, key_perfix: str, img_url=None) -> str:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        )

        if not img_file.name:
            raise serializers.ValidationError("파일의 이름이 없습니다")

        file_extension = img_file.name.split(".")[-1]
        key = f"{key_perfix}/{uuid.uuid4()}.{file_extension}"

        try:
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            )

            key = img_url.replace(f"{settings.NCP_BUCKET_URL}/", "") if img_url else ""
            s3_client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
        except ClientError as e:
            logger.error(f"NCP delete error: {str(e)}")

    @extend_schema(
        summary="사용자 프로필 조회",
        description="인증된 사용자의 프로필 정보를 조회합니다.",
        responses={200: UserProfileSerializer},
        tags=["User Profile"],
    )
    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        data = serializer.data
        return Response(
            {
                "message": f"{data['nick_name']}의 정보가 정상적으로 반환되었습니다",
                "user": data,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="사용자 프로필 수정",
        description="인증된 사용자의 닉네임과 프로필 이미지를 수정합니다.",
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer},
        tags=["User Profile"],
        parameters=[
            OpenApiParameter(
                name="nick_name",
                type=OpenApiTypes.STR,
                location="form",
                description="수정할 닉네임",
                required=False,
            ),
            OpenApiParameter(
                name="profile_img",
                type=OpenApiTypes.BINARY,
                location="form",
                description="수정할 프로필 이미지",
                required=False,
            ),
        ],
    )
    def patch(self, request, *args, **kwargs):
        logger.info("PATCH request.data: %s", request.data)
        logger.info("PATCH request.FILES: %s", request.FILES)

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        user_data = serializer.data
        return Response(
            {"message": "회원 정보가 수정되었습니다.", "user": user_data},
            status=status.HTTP_200_OK,
        )

    def perform_update(self, serializer):
        logger.info("Performing update...")

        user = self.request.user
        old_img_url = user.profile_img
        profile_img = self.request.FILES.get("profile_img")
        logger.info("Profile image: %s", profile_img)

        try:
            # 닉네임 업데이트
            if "nick_name" in serializer.validated_data:
                user.nick_name = serializer.validated_data["nick_name"]

            # 프로필 이미지 업데이트
            if profile_img and isinstance(profile_img, InMemoryUploadedFile):
                logger.info("Uploading file: %s", profile_img.name)
                new_img_url = self._upload_to_ncp(profile_img, "users/profile")
                user.profile_img = new_img_url
                logger.info("File uploaded successfully: %s", user.profile_img)

                # 기존 이미지 삭제
                if old_img_url and self._is_ncp_image(old_img_url):
                    self._delete_from_ncp(old_img_url)
                    logger.info("Old image deleted: %s", old_img_url)
            else:
                logger.warning("No valid profile image found")

            # 사용자 정보 저장
            user.is_updated = timezone.now()
            user.save()
            serializer.save()
            logger.info("Update complete")

        except Exception as e:
            logger.error("Profile update error: %s", e)
            raise serializers.ValidationError(
                f"프로필 수정 중 오류가 발생했습니다: {str(e)}"
            )


class UserWithdrawView(generics.GenericAPIView):
    serializer_class = NicknameCheckSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="회원 탈퇴 요청",
        description="회원 탈퇴 요청을 처리합니다. 닉네임 일치 여부를 확인하고, 50일 후 사용자 정보를 삭제합니다.",
        parameters=[
            OpenApiParameter(
                name="input_nick_name",
                description="입력한 사용자 닉네임",
                required=True,
                type=str,
            )
        ],
        request=NicknameCheckSerializer,
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        },
        tags=["🚨🚨🚨 User Withdraw 🚨🚨🚨"],
    )
    def delete(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        input_nick_name = serializer.validated_data["input_nick_name"]
        user = self.request.user

        if user.nick_name != input_nick_name:
            return Response(
                {"message": "입력한 닉네임과 일치하지 않습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.withdraw_at = timezone.now()
        delete_date = timezone.now() + datetime.timedelta(days=50)
        user.is_active = 0  # is_active 필드 값을 False = 0으로 설정
        user.save()  # 변경 사항을 데이터베이스에 저장

        request_data = {
            "message": "계정탈퇴가 요청되었습니다. 50일후 사용자 정보는 완전히 삭제가 됩니다.",
            "deletion_date": delete_date,
        }
        return Response({"data": request_data}, status=status.HTTP_200_OK)
