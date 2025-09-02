from html2text import HTML2Text
from functools import wraps
from django.contrib.auth.decorators import login_required

# Configuration of html2text
text_maker = HTML2Text()
text_maker.ignore_tables = True
text_maker.images_to_alt = True
text_maker.body_width = 1000
text_maker_translation = str.maketrans('[]', '  ')

def html_to_text(html_content):
    return text_maker.handle(html_content).translate(text_maker_translation).replace("**", "*")


# Login required with ability to set custom login message
def login_required_with_message(message="Tu dois être connecté pour accéder à cette page."):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                request.session['login_message'] = message
                request.session['login_next'] = None # Stored to be able to invalidate message in case the querystring changes and not this session variable. Will be set in the view.
            # apply normal login_required check
            return login_required(view_func)(request, *args, **kwargs)
        return _wrapped_view
    return decorator
