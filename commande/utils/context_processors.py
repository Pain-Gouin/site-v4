from django.conf import settings


def export_debug_status_data(request):
    return {"IS_PROD": settings.PROD, "GIT_COMMIT": settings.GIT_COMMIT}
