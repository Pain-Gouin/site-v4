from html2text import HTML2Text

# Configuration of html2text
text_maker = HTML2Text()
text_maker.ignore_tables = True
text_maker.images_to_alt = True
text_maker.body_width = 1000
text_maker_translation = str.maketrans('[]', '  ')

def html_to_text(html_content):
    return text_maker.handle(html_content).translate(text_maker_translation).replace("**", "*")