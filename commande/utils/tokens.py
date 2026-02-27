from django.contrib.auth.tokens import PasswordResetTokenGenerator


class VerifiedUserTokenGenerator(PasswordResetTokenGenerator):
    # Same as PasswordResetToken, but only invalidates after a certain time
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.verified_genuine_user}"
