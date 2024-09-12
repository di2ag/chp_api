from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope

from .serializers import UserSerializer


class UserDetails(APIView):
    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope]

    def get(self, request):
        user = request.user
        return Response(UserSerializer(user).data)
