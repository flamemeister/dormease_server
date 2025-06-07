from weasyprint import HTML
from django.template.loader import render_to_string
from datetime import datetime

def generate_contract_pdf(application):
    student = application.student

    html = render_to_string("contracts/contract_template.html", {
        "full_name": f"{student.last_name} {student.first_name}",
        "iin": application.iin,
        "city": application.city,
        "email": student.email,
        "submitted_date": application.created_at.strftime("%d.%m.%Y"),
        "contract_id": application.id
    })

    output_path = f"/tmp/contract_{application.id}.pdf"
    HTML(string=html).write_pdf(output_path)
    return output_path
