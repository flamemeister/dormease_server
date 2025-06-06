from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from asn1crypto import cms

from pypdf import PdfReader, PdfWriter  # только pypdf!
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign.signers.cms_embedder import PdfCMSEmbedder, SigObjSetup, SigIOSetup
from pyhanko.sign.signers.pdf_byterange import SignatureObject

from pypdf import PdfReader, PdfWriter  # <== ОБЯЗАТЕЛЬНО ТАК

from pypdf import PdfReader, PdfWriter  # <== ОБЯЗАТЕЛЬНО ТАК

from io import BytesIO

def prepare_pdf_for_signature(pdf_bytes: bytes) -> bytes:
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.add_blank_signature_field(
        sig_field_name="Sig1",
        page_number=0,
        box=(50, 50, 250, 100)
    )

    output = BytesIO()
    writer.write(output)
    return output.getvalue()



def generate_signature_info_page(info: dict) -> BytesIO:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.drawString(100, 750, f"👤 Подписант: {info['subject'].get('common_name', '—')}")
    c.drawString(100, 730, f"🆔 ИИН: {info['subject'].get('serial_number', '—')}")
    c.drawString(100, 710, f"📅 Действует: {info['not_before']} — {info['not_after']}")
    c.save()
    buffer.seek(0)
    return buffer


def extract_signer_info(cms_bytes: bytes) -> dict:
    content_info = cms.ContentInfo.load(cms_bytes)
    signed_data = content_info['content']
    signer_infos = signed_data['signer_infos']
    if not signer_infos:
        return {"subject": {}, "not_before": "?", "not_after": "?"}

    certs = signed_data['certificates']
    signer_cert = None

    for cert in certs:
        cert_obj = cert.chosen
        issuer = cert_obj.issuer.native
        serial = cert_obj.serial_number

        for signer in signer_infos:
            signer_issuer = signer['sid'].chosen['issuer'].native
            signer_serial = signer['sid'].chosen['serial_number']
            if signer_issuer == issuer and signer_serial == serial:
                signer_cert = cert_obj
                break

    if not signer_cert:
        return {"subject": {}, "not_before": "?", "not_after": "?"}

    return {
        "subject": signer_cert.subject.native,
        "not_before": signer_cert['tbs_certificate']['validity']['not_before'].native.strftime('%Y-%m-%d'),
        "not_after": signer_cert['tbs_certificate']['validity']['not_after'].native.strftime('%Y-%m-%d'),
    }


def add_info_page_to_pdf(original_pdf: bytes, info_page: BytesIO) -> bytes:
    reader = PdfReader(BytesIO(original_pdf))
    info = PdfReader(info_page)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.add_page(info.pages[0])

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def embed_cms_into_pdf(pdf_bytes: bytes, cms_bytes: bytes, field_name="Sig1") -> bytes:
    pdf_io = BytesIO(pdf_bytes)
    writer = IncrementalPdfFileWriter(pdf_io)
    sig_obj = SignatureObject(bytes_reserved=16384)
    embedder = PdfCMSEmbedder()

    coro = embedder.write_cms(
        field_name=field_name,
        writer=writer,
        existing_fields_only=True
    )
    next(coro)
    coro.send(SigObjSetup(sig_placeholder=sig_obj))
    _, output = coro.send(SigIOSetup(md_algorithm="sha256"))

    try:
        coro.send(cms_bytes)
    except StopIteration:
        pass

    return output.getvalue()
