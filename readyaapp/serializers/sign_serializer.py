
from django.contrib.auth import authenticate  
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

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


    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("email is required")

        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("this email is already in use")

        return value

   
    def validate_full_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("full name is required")

        if len(value.split()) < 2:
            raise serializers.ValidationError("please provide both first name and last name")

        return value

    
    def validate_password(self, value):
        try:
            validate_password(value)
        except Exception as e:
            raise serializers.ValidationError(list(e.messages))

        return value

   
    def validate(self, data):
        if data.get("password") != data.get("confirm_password"):
            raise serializers.ValidationError({
                "confirm_password": "passwords do not match"
            })

        return data

   
    def create(self, validated_data):
        validated_data.pop("confirm_password")
        full_name = validated_data.pop("full_name")

        names = full_name.split(" ", 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ""

        user = User.objects.create_user(
            username=validated_data["email"],
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
        email = data.get("email")
        password = data.get("password")

        
        user = User.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError({
                "email": "user with this email does not exist"
            })

        
        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError({
                "password": "password is incorrect"
            })

       
        if not user.is_active:
            raise serializers.ValidationError({
                "email": "user is inactive"
            })

        data["user"] = user
        return data
    


# Logout serializer

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()




# Password reset serializerss

from rest_framework import serializers

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField(min_length=8)

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match"
            })
        return data