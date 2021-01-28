from .models import Token
import uuid


def tokenGeneartion(user_id):
    """
    This will be used to generate token for respective user
    """

    token = uuid.uuid4()
    Token.objects.create(user=user_id, token=token)
    return token

