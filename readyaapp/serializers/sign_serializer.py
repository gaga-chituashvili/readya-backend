from rest_framework import serializers
from django.contrib.auth import get_user_model

from django.contrib.auth import authenticate

User = get_user_model()
    
class RegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "full_name", "password", "confirm_password"]
        extra_kwargs = {
            "password": {"write_only": True}
        }

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match")
        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        full_name = validated_data.pop("full_name")

        
        names = full_name.split(" ", 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ""

        user = User.objects.create_user(
            username=validated_data["email"],  # email = username
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=first_name,
            last_name=last_name,
        )

        return user
    
# Login serializer

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(
            username=data["email"],
            password=data["password"]
        )

        if not user:
            raise serializers.ValidationError("Invalid credentials")

        if not user.is_active:
            raise serializers.ValidationError("User is inactive")

        data["user"] = user
        return data

# Logout serializer

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()