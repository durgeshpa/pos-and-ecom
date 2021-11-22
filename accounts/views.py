from django.shortcuts import render
import logging

logger = logging.getLogger(__name__)


def terms_and_conditions(request):
    return render(request, 'accounts/terms_and_conditions.html')

def privacy_policy(request):
	logger.exception('Something went wrong!')
	return render(request, 'accounts/privacy_policy.html')
