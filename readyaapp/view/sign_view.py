from rest_framework.response import Response
from rest_framework import generics
from django.contrib.auth.models import User
from readyaapp.serializers.sign_serializer import LoginSerializer, RegisterSerializer  
from rest_framework import generics, status
from rest_framework_simplejwt.tokens import RefreshToken 
from readyaapp.serializers.sign_serializer import LogoutSerializer
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated


#-------------- registration view -------------------

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]



#-------------- login view -------------------

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.get_full_name(),
            }
        }, status=status.HTTP_200_OK)
    

#-------------- logout view -------------------




class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer

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

        return Response(
            {"detail": "Successfully logged out"},
            status=status.HTTP_205_RESET_CONTENT
        )
    




class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "email": request.user.email
        })