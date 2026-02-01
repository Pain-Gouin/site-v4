from django.urls import path

from . import views
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

urlpatterns = [
    path("", views.index, name="index"),
    path("mentions", views.mentions, name="mentions"),
    path("contact", views.contact, name="contact"),
    path("login", views.login_page, name="login"),
    path("login/check-email/", views.check_email, name="check-email"),
    path("login/reset-password", views.reset_password_ajax, name='password_reset_ajax'),
    path("logout", views.logout_user, name="logout"),
    path("signup", views.signup, name="signup"),
    path("signup/<uidb64>/<token>/", views.finish_signup_page, name="finish_signup"),
    path("update", views.update_user_page, name="update"),
    path("commande", views.commande, name="commande"),
    path("recharge", views.recharge, name="recharge"),
    path("livreur", views.livreur, name="livreur"),
    path("historique", views.historique, name="historique"),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="commande/password_reset_confirm.html",
            success_url=reverse_lazy("password_change_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-change-complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="commande/password_change_complete.html"
        ),
        name="password_change_complete",
    ),
    path(
        "password-change/",
        auth_views.PasswordChangeView.as_view(
            template_name="commande/password_change.html",
            success_url=reverse_lazy("password_change_complete"),
        ),
        name="password_change",
    ),
    path("del-order/<order>/", views.del_order, name="del_order"),
]
