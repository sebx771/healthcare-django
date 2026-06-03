from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        try:
            token['rol'] = user.perfil.rol
        except Exception:
            token['rol'] = None
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        try:
            data['rol'] = self.user.perfil.rol
        except Exception:
            data['rol'] = None
        return data
