from django.shortcuts import render

def terms_and_conditions(request):
    return render(request, 'accounts/terms_and_conditions.html')

def privacy_policy(request):
    return render(request, 'accounts/privacy_policy.html')
