from asn1crypto import cms, x509
from datetime import datetime

def verify_and_extract_info(cms_bytes):
    try:
        content_info = cms.ContentInfo.load(cms_bytes)
        if content_info['content_type'].native != 'signed_data':
            return False, {"error": "Это не CMS-подпись (signed_data)"}

        signed_data = content_info['content']
        signer_infos = signed_data['signer_infos']

        if not signer_infos:
            return False, {"error": "Нет подписантов в CMS"}

        signer = signer_infos[0]
        sid = signer['sid']
        issuer_serial = sid.chosen
        serial_number = issuer_serial['serial_number'].native

        cert = next(
            (
                cert.chosen
                for cert in signed_data['certificates']
                if cert.name == 'certificate' and cert.chosen.serial_number == serial_number
            ),
            None
        )

        if not cert:
            return False, {"error": "Сертификат подписанта не найден"}

        subject = cert.subject
        fio = subject.native.get("common_name", "Неизвестно")
        iin = subject.native.get("serial_number", "Не указано")
        not_before = cert["tbs_certificate"]["validity"]["not_before"].native
        not_after = cert["tbs_certificate"]["validity"]["not_after"].native

        return True, {
            "fio": fio,
            "iin": iin,
            "valid_from": not_before.strftime("%d.%m.%Y %H:%M"),
            "valid_to": not_after.strftime("%d.%m.%Y %H:%M"),
            "serial_number": str(cert.serial_number)
        }

    except Exception as e:
        return False, {"error": f"Ошибка при разборе CMS: {str(e)}"}


# deprecated alias, if needed for compatibility
def extract_signer_info(cms_bytes):
    valid, data = verify_and_extract_info(cms_bytes)
    return data if valid else None
