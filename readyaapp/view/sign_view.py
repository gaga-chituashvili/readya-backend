from rest_framework.response import Response
from rest_framework import generics
from django.contrib.auth import get_user_model
from readyaapp.serializers.sign_serializer import LoginSerializer, RegisterSerializer  
from rest_framework import generics, status
from rest_framework_simplejwt.tokens import RefreshToken 
from readyaapp.serializers.sign_serializer import LogoutSerializer
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from google.oauth2 import id_token
from google.auth.transport import requests
from rest_framework.decorators import api_view

from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from readyaapp.serializers.sign_serializer import PasswordResetRequestSerializer,PasswordResetConfirmSerializer


User = get_user_model()

#-------------- registration view -------------------
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)

        user = User.objects.get(email=request.data["email"])
        refresh = RefreshToken.for_user(user)

        response.set_cookie(
            key="access_token",
            value=str(refresh.access_token),
            httponly=True,
            secure=True,
            samesite="None"
        )

        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite="None"
        )

        return response


#-------------- login view -------------------

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        response = Response({
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": f"{user.first_name} {user.last_name}",
            }
        }, status=status.HTTP_200_OK)

       
        response.set_cookie(
            key="access_token",
            value=str(refresh.access_token),
            httponly=True,
            secure=True, 
            samesite="None"
        )

       
        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=True, 
            samesite="None"
        )

        return response
    

#-------------- logout view -------------------




class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data["refresh"]

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response(
                {"detail": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST
            )

        response = Response(
            {"detail": "Successfully logged out"},
            status=status.HTTP_205_RESET_CONTENT
        )

       
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response
    

#-------------- profile view -------------------



class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        full_name = " ".join(filter(None, [
            user.first_name,
            user.last_name
        ]))

        return Response({
            "email": user.email,
            "full_name": full_name,
            "subscription_plan": user.subscription_plan.name if user.subscription_plan else None,
            "subscription_end": user.subscription_end,
            "is_active_subscription": user.has_active_subscription()
        })

#-------------- google auth view -------------------


@api_view(['POST'])
def google_auth(request):
    token = request.data.get('token')

    if not token:
        return Response({"error": "No token provided"}, status=400)

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request()
        )

        email = idinfo['email']
        name = idinfo.get('name', '')
        picture = idinfo.get('picture')

        user, created = User.objects.get_or_create(
            username=email,
            defaults={
                "email": email,
                "first_name": name,
            }
        )

        if created:
            user.set_unusable_password()
            user.save()

        refresh = RefreshToken.for_user(user)

        response = Response({
            "user": {
                "email": user.email,
                "name": user.first_name,
                "picture": picture,
            },
            "is_new_user": created
        })

        response.set_cookie(
            key="access_token",
            value=str(refresh.access_token),
            httponly=True,
            secure=True,
            samesite="None"
        )

        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite="None"
        )

        return response

    except Exception:
        return Response({"error": "Invalid Google token"}, status=400)
    


    #-------------- password reset view -------------------




class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        user = User.objects.filter(email=email).first()


        if user:
            uid = str(user.pk)
            token = default_token_generator.make_token(user)


            reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"

            send_mail(
                "Reset password",
                f"Click here:\n{reset_link}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )

        return Response({
            "detail": "If this email exists, reset instructions were sent"
        })



#-------------- password reset confirm view -------------------


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        password = serializer.validated_data["password"]

        try:
            user = User.objects.get(pk=uid)
        except User.DoesNotExist:
            return Response({"error": "Invalid link"}, status=400)

        if not default_token_generator.check_token(user, token):
            return Response({"error": "Invalid or expired token"}, status=400)

        user.set_password(password)
        user.save()

        return Response({"detail": "Password changed successfully"})