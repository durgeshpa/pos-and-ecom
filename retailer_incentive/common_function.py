from accounts.models import User


def get_user_id_from_token(request):
    """
        If Token is valid get User from token
    """
    if request.user.id:
        if User.objects.filter(id=request.user.id).exists():
            user = User.objects.filter(id=request.user.id).last()
            return user
        return "Please provide Token"
