from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.conf import settings
from . import forms

from datetime import datetime

# Create your views here.
def index(request):
    return render(request, "commande/main.html")

def login_page(request):
    invalidCredential=False
    form = forms.LoginForm()
    if request.method == 'POST':
        form = forms.LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                username = form.cleaned_data["username"],
                password = form.cleaned_data["password"],
            )
            user.last_login = datetime.now
            if user is not None :
                login(request,user)
                return redirect(index)
            else:
                invalidCredential = True
    return render(request, 'commande/login.html', context={'form': form, "invalidCredential":invalidCredential})

def logout_user(request):
    logout(request)
    return redirect(index)

def signup_page(request):
    form = forms.SignupForm()
    if request.method == 'POST':
        form = forms.SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)
    return render(request, 'commande/signup.html', context={'form': form})