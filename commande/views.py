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
    livraison_query = Livraison.objects.exclude(date__lt = datetime.today().strftime('%Y-%m-%d')).order_by("date")
    produit_query = list(Produit.objects.all())
    categorie_query = CategorieProduit.objects.all()
    successOrder = request.GET.get('successOrder',False)

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
            if int(quantity) > 0:
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

            add_to_livraison(date,order)
            return redirect("./commande?successOrder=True")


    context = {'produit': produit, 'categorie':categorie_query, 'livraison':livraison_query, "errorFondInsuffisant":errorFondInsuffisant, "successOrder":successOrder}
    return render(request, 'commande/order.html', context)

def add_to_livraison(date, commande):
    livraison = Livraison.objects.get(date = date).produit
    liste_commande = json.loads(commande)

    if livraison == ['None']:
        livraison.pop()
    else:
        livraison = json.loads(livraison)

    for produit in liste_commande:
        compteur = 0
        for liv in livraison:
            if produit[0] == liv[0]:
                a = int(liv[1]) + int(produit[1])
                liv[1] = str(a)
                break
            compteur +=1
        if compteur == len(livraison) and int(produit[1])!=0:
            livraison.append(produit.copy()) 
    
    update =  Livraison.objects.filter(date=date).update(produit = json.dumps(livraison))
    return

def add_livraison_batiment(batiment, commande_batiment, produit_client):
    if commande_batiment[batiment] == []:
        commande_batiment[batiment] = produit_client.copy()
    else : 
        for comm_client in produit_client:
            i = 0
            for prod in commande_batiment[batiment]:
                if prod[0] == comm_client[0]:
                        a = str(int(prod[1]) + int(comm_client[1]))
                        prod[1] = a
                        break
                i += 1
            if i==len(commande_batiment[batiment]):           
                commande_batiment[batiment].append(comm_client.copy())
    print(produit_client)
    return commande_batiment

@login_required
def livreur(request):
    produit = ['None']
    try:
        livraison_query = Livraison.objects.get(date = datetime.today().strftime('%Y-%m-%d'))
        produit = livraison_query.produit
    except:
        livraison_query = None

    commande = list(Commande.objects.filter(date = datetime.today().strftime('%Y-%m-%d')).order_by("chambre"))
    commande_list = []
    commande_batiment = [[],[],[],[],[],[]]

    for comm in commande :
        produit_client = json.loads(comm.produit)
        produit_client2 = json.loads(comm.produit)
        commande_list.append([comm.chambre, produit_client])
        match comm.chambre[0]:
            case 'A':
                commande_batiment = add_livraison_batiment(0, commande_batiment, produit_client2)
            case 'B':
                commande_batiment = add_livraison_batiment(1, commande_batiment, produit_client2)
            case 'C':
                commande_batiment = add_livraison_batiment(2, commande_batiment, produit_client2)
            case 'D':
                commande_batiment = add_livraison_batiment(3, commande_batiment, produit_client2)
            case 'E':
                commande_batiment = add_livraison_batiment(4, commande_batiment, produit_client2)
            case 'F':
                commande_batiment = add_livraison_batiment(5, commande_batiment, produit_client2)

    if produit == ['None']:
        produit = False
    else :
        produit = json.loads(produit)

    context = {'livraison':livraison_query, 'produit':produit, 'commande':commande_list, 'commande_batiment':commande_batiment}
    return render(request, "commande/livreur.html", context)