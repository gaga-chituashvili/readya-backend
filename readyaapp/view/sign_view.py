from rest_framework import generics
from readyaapp.models import User
from readyaapp.serializers.sign_serializer import LoginSerializer, RegisterSerializer   


#-------------- registration view -------------------

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer



#-------------- login view -------------------

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        return Response({
            "message": "Login successful",
            "email": user.email,
            "full_name": user.full_name,
        }, status=status.HTTP_200_OK)