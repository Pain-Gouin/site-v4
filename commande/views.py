from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from . import forms

# Create your views here.
def index(request):
    return render(request, "commande/main.html")

def login_page(request):
    message=""
    form = forms.LoginForm()
    if request.method == 'POST':
        form = forms.LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                username = form.cleaned_data["username"],
                password = form.cleaned_data["password"],
            )
            if user is not None :
                login(request,user)
                return redirect(index)
            else:
                message ="Idenftifiants Invalides !"
    return render(request, 'commande/login.html', context={'form': form, "message":message})

def logout_user(request):
    logout(request)
    return redirect(index)