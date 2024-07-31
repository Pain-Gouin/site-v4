from django.urls import path

from . import views
from .views import ResetPasswordView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_page, name="login"),
    path("logout", views.logout_user, name="logout"),
    path("signup", views.signup_page, name="signup"),
    path("update", views.update_user_page, name="update"),
    path("commande", views.commande, name="commande"),
    path("livreur", views.livreur, name="livreur"),
    path('password-reset/', ResetPasswordView.as_view(), name='password_reset'),
    path('password-reset-confirm/<uidb64>/<token>/',auth_views.PasswordResetConfirmView.as_view(template_name='commande/password_reset_confirm.html'),name='password_reset_confirm'),
    path('password-reset-complete/',auth_views.PasswordResetCompleteView.as_view(template_name='commande/password_reset_complete.html'),name='password_reset_complete'),
]