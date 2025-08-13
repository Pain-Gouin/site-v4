from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.views import PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from datetime import datetime, time
from django.utils import timezone

from . import forms

import json

from .models import Produit, CategorieProduit, Commande, Livraison

# Create your views here.
def index(request):
    return render(request, "commande/main.html")

def mentions(request):
    return render(request, "commande/mentions.html")

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
            request.user.last_login = datetime.now
            if user is not None :
                login(request,user)
                return redirect(index)
            else:
                invalidCredential = True
    return render(request, 'commande/login.html', context={'form': form, "invalidCredential":invalidCredential})

class ResetPasswordView(SuccessMessageMixin, PasswordResetView):
    template_name = 'commande/password_reset.html'
    email_template_name = 'mail/password_reset_mail.html'
    subject_template_name = 'mail/password_reset_subject.txt'
    search_field = ['email']
    from_email = settings.EMAIL_HOST_USER
    success_message = "We've emailed you instructions for setting your password, " \
                      "if an account exists with the email you entered. You should receive them shortly." \
                      " If you don't receive an email, " \
                      "please make sure you've entered the address you registered with, and check your spam folder."
    success_url = reverse_lazy("index")

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
            request.user.email = request.user.username
            receiver_email = request.user.username
            request.user.save()
            template_name = "mail/signup_mail.html"
            convert_to_html_content =  render_to_string(
                template_name=template_name,
                context = {
                    'prenom':request.user.first_name,
                }
            )
            plain_message = strip_tags(convert_to_html_content)

            send_mail(
                subject="Inscription confirmée",
                message=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[receiver_email,],
                html_message=convert_to_html_content,
                fail_silently=True
            )
            return redirect(settings.LOGIN_REDIRECT_URL)
    return render(request, 'commande/signup.html', context={'form': form})

@login_required
def update_user_page(request):
    if request.method == 'POST':
        form = forms.UpdateForm(data=request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect(settings.LOGIN_REDIRECT_URL)
    else:
        form = forms.UpdateForm(instance=request.user)

    return render(request, "commande/update.html", context={"form":form})


@login_required
def commande(request):
    errorFondInsuffisant = False
    order = []

    current_time = timezone.now()
    today = current_time.date()

    livraison_query = Livraison.objects.modifiable()


    produit_query = list(Produit.objects.all())
    categorie_query = CategorieProduit.objects.all()
    successOrder = request.GET.get('successOrder',False)

    produit = produit_query

    if request.method == 'POST':
        if request.user.is_authenticated:
            user = request.user.get_username()
            solde = request.user.credit

        total_commande = 0

        bought_prod = []
        for prod in produit_query:
            quantity = request.POST["quantity" + str(prod.id)]
            print(produit_query)
            total_commande += int(quantity)*prod.prix
            if int(quantity) > 0:
                bought_prod.append({"object": prod, "quantity": quantity, "price": int(quantity)*prod.prix})
                order.append([prod.nom, quantity])
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

            receiver_email = request.user.username
            template_name = "mail/order_mail.html"
            convert_to_html_content =  render_to_string(
                template_name=template_name,
                context = {
                    'prenom': request.user.first_name,
                    'date': date,
                    'commande': bought_prod,
                    'total': total_commande,
                    'chambre': chambre,
                    "request": request,
                    "media_url": settings.MEDIA_URL
                }
            )
            plain_message = strip_tags(convert_to_html_content)

            send_mail(
                subject="Confirmation de commande",
                message=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[receiver_email,],
                html_message=convert_to_html_content,
                fail_silently=True
            )

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


@login_required
def historique(request):
    user_order = Commande.objects.filter(client=request.user.username).order_by("-date")
    historique = []

    for commande in user_order:
        passe = commande.est_modifiable
        historique.append({"date":commande.date, "produits":json.loads(commande.produit), "total":commande.total_commande, "passe":passe, "id":commande.id})

    context = {"historique":historique}
    return render(request, "commande/historique.html", context)

@login_required
def del_order(request, order):
    query_order = Commande.objects.get(id = order)
    if query_order.client != request.user.username or query_order.date <= datetime.today().date():
        return redirect(settings.LOGIN_REDIRECT_URL)
    else:
        request.user.credit += query_order.total_commande
        request.user.save()
        
        del_to_livraison(query_order.date,query_order.produit)

        query_order.delete()

        return redirect("historique")

def del_to_livraison(date, commande):
    livraison = Livraison.objects.get(date = date).produit
    liste_commande = json.loads(commande)

    if livraison == ['None']:
        livraison.pop()
    else:
        livraison = json.loads(livraison)

    for produit in liste_commande:
        for liv in livraison:
            if produit[0] == liv[0]:
                a = int(liv[1]) - int(produit[1])
                if a == 0:
                    livraison.remove(liv)
                else:
                    liv[1] = str(a)
                break
    
    update =  Livraison.objects.filter(date=date).update(produit = json.dumps(livraison))
    return