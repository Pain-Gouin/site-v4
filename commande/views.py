from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings

from . import forms

from datetime import datetime
import json

from .models import Produit, CategorieProduit, Commande, Livraison

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


@login_required
def commande(request):
    errorFondInsuffisant = False
    order = []
    livraison_query = Livraison.objects.exclude(date__lt = datetime.today().strftime('%Y-%m-%d'))
    produit_query = list(Produit.objects.all())
    categorie_query = CategorieProduit.objects.all()

    number_of_product = len(produit_query)

    produit = []

    for i in range(number_of_product):
        a = forms.ProductOrderForm()
        temp = []
        temp.append(produit_query[i])
        temp.append(a)
        produit.append(temp)

    if request.method == 'POST':
        if request.user.is_authenticated:
            user = request.user.get_username()
            solde = request.user.credit

        total_commande = 0
        
        for i in range(1,len(produit_query)+1):
            product = produit_query[i-1].nom
            quantity = request.POST["quantity" + str(i)]
            total_commande += int(quantity)*produit_query[i-1].prix
            order.append([product, quantity])
        order = json.dumps(order)

        if total_commande > solde:
            errorFondInsuffisant = True
        else:
            chambre = request.POST["chambre"]
            date = list(Livraison.objects.filter(id = request.POST["date"]))[0].date
            solde -= total_commande
            request.user.credit = solde
            request.user.save()

            comm = Commande(client = user, date = date, produit = order, chambre = chambre, total_commande = total_commande)
            comm.save()


    context = {'produit': produit, 'categorie':categorie_query, 'livraison':livraison_query, "errorFondInsuffisant":errorFondInsuffisant}
    return render(request, 'commande/order.html', context)