import logging
import os
from datetime import datetime, timezone

import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from users.serializers import (
    LogoutSerializer,
    NicknameCheckSerializer,
    UserProfileSerializer,
)

User = get_user_model()

logger = logging.getLogger(__name__)


class SocialLoginView(APIView):
    def post(self, request, provider):
        auth_code = request.data.get("code")  # 프론트에서 받은 인가 코드
        if not auth_code:
            return Response(
                {"error": "Authorization code is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 인가 코드를 access_token으로 변환
        access_token = self.get_access_token(provider, auth_code)
        if not access_token:
            return Response(
                {"error": "Failed to retrieve access token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # access_token을 사용하여 사용자 정보 가져오기
        user_info = self.get_social_user_info(provider, access_token)
        if not user_info:
            return Response(
                {"error": "Invalid social token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 사용자 정보로 DB 조회 및 저장
        user, created = User.objects.get_or_create(
            email=user_info["email"],
            provider=provider,
            defaults={
                "nick_name": user_info.get("nick_name"),
                "profile_img": user_info.get("profile_image"),
            },
        )

        # JWT 토큰 생성
        token = RefreshToken.for_user(user)
        return Response(
            {
                "token": str(token.access_token),
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
            "client_id": "KAKAO_CLIENT_ID",
            "redirect_uri": "KAKAO_CALLBACK_URL",
            "code": auth_code,
            "client_secret": "KAKAO_CLIENT_SECRET",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.post(url, data=data, headers=headers)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None

    def get_naver_access_token(self, auth_code):
        # 네이버 인가 코드 → Access Token 변환
        url = "https://nid.naver.com/oauth2.0/token"
        params = {
            "grant_type": "authorization_code",
            "client_id": "NAVER_CLIENT_ID",
            "client_secret": "NAVER_CLIENT_SECRET",
            "code": auth_code,
            "state": "random_state_string",  # 보안 강화를 위해 사용
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None

    def get_google_access_token(self, auth_code):
        # 구글 인가 코드 → Access Token 변환
        url = "https://oauth2.googleapis.com/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": "GOOGLE_CLIENT_ID",
            "client_secret": "GOOGLE_CLIENT_SECRET",
            "redirect_uri": "GOOGLE_CALLBACK_URL",
            "code": auth_code,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.post(url, data=data, headers=headers)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None

    def get_social_user_info(self, provider, access_token):

        # access_token -> 소셜 사용자 정보 가져오기
        if provider == "kakao":
            url = "https://kapi.kakao.com/v2/user/me"
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return {
                    "email": data["kakao_account"].get("email"),
                    "nick_name": data["properties"].get("nickname"),
                    "profile_image": data["properties"].get("profile_image"),
                }
        elif provider == "naver":
            url = "https://openapi.naver.com/v1/nid/me"
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()["response"]
                return {
                    "email": data.get("email"),
                    "nick_name": data.get("nickname"),
                    "profile_image": data.get("profile_image"),
                }
        elif provider == "google":
            url = "https://www.googleapis.com/oauth2/v3/userinfo"
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return {
                    "email": data.get("email"),
                    "nick_name": data.get("name"),
                    "profile_image": data.get("picture"),
                }
        return None


class LogoutView(generics.CreateAPIView):
    serializer_class = LogoutSerializer

    @extend_schema(
        summary="로그아웃 처리",
        description="로그아웃 처리합니다. 로그아웃과 동시에 token값은 blacklist에 보내서 다시 사용 불가",
        tags=["Logout"],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.perform_create(serializer)

    def perform_create(self, serializer):
        try:
            refresh_token = serializer.validated_data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"message": "로그아웃 되었습니다."}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer
    queryset = User.objects.all()

    def get_object(self):
        return self.request.user

    @extend_schema(
        summary="사용자 프로필 조회",
        description="인증된 사용자의 프로필 정보를 조회합니다.",
        responses={200: UserProfileSerializer},
        tags=["User Profile"],
    )
    def get(self, request, *args, **kwargs):  # GET 메서드 처리
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
    )
    def post(self, request, *args, **kwargs):  # POST 메서드만 처리
        if request.method not in ["POST"]:
            return HttpResponseNotAllowed(["POST"])

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
        user = self.request.user
        profile_img = self.request.FILES.get("profile_img")
        if profile_img:
            upload_dir = "/app/media/profile"
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, f"{user.id}_{profile_img.name}")

            with open(file_path, "wb+") as destination:
                for chunk in profile_img.chunks():
                    destination.write(chunk)

            user.profile_img = f"/media/profile/{user.id}_{profile_img.name}"

        user.is_updated = timezone.now()
        user.save()
        serializer.save()


class UserWithdrawView(generics.GenericAPIView):
    serializer_class = NicknameCheckSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="회원 탈퇴 요청",
        description="회원 탈퇴 요청을 처리합니다. 닉네임 일치 여부를 확인하고, 50일 후 사용자 정보를 삭제합니다.",
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

        # user.withdraw_at = timezone.now() # 해당필드가 없어서 주석처리함

        delete_date = timezone.now() + datetime.timedelta(days=50)
        user.is_active = False
        user.save()

        request_data = {
            "message": "계정탈퇴가 요청되었습니다. 50일후 사용자 정보는 완전히 삭제가 됩니다.",
            "deletion_date": delete_date,
        }
        return Response({"data": request_data}, status=status.HTTP_200_OK)
