from weasyprint import HTML
from django.template.loader import render_to_string
import tempfile

def generate_contract_pdf(application):
    html_string = render_to_string("contracts/contract_template.html", {"app": application})
    html = HTML(string=html_string)
    result = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    html.write_pdf(target=result.name)
    return result.name
