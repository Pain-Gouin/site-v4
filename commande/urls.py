from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_page, name="login"),
    path("logout", views.logout_user, name="logout"),
    path("signup", views.signup_page, name="signup"),
    path("commande", views.commande, name="commande"),
    path("livreur", views.livreur, name="livreur")
]