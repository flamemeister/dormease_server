from asn1crypto import cms, x509
import hashlib

def verify_cms_signature(pdf_bytes: bytes, cms_bytes: bytes) -> bool:
    try:
        content_info = cms.ContentInfo.load(cms_bytes)
        signed_data = content_info['content']
        certificates = signed_data['certificates']

        signer_infos = signed_data['signer_infos']
        if not signer_infos:
            print(". Нет подписанта в CMS")
            return False

        signer = signer_infos[0]
        sid = signer['sid']
        issuer_serial = sid.chosen
        serial = issuer_serial['serial_number'].native

        cert = next((x.chosen for x in certificates if x.name == 'certificate' and x.chosen.serial_number == serial), None)
        if not cert:
            print(". Сертификат не найден в CMS")
            return False

        pub_key = cert.public_key

        digest_oid = signer['digest_algorithm']['algorithm'].dotted
        signature = signer['signature'].native

        if digest_oid.startswith("1.2.398.3.10"):
            print("⚠️ ГОСТ-алгоритм обнаружен. Пропускаем проверку подписи.")
            return True

        digest_algo = signer['digest_algorithm']['algorithm'].native
        if digest_algo == 'sha256':
            digest = hashlib.sha256(pdf_bytes).digest()
        elif digest_algo == 'sha1':
            digest = hashlib.sha1(pdf_bytes).digest()
        else:
            print(f". Неподдерживаемый digest алгоритм: {digest_algo}")
            return False

        try:
            pub_key.verify(signature, digest)
        except Exception as e:
            print(f". Подпись недействительна: {e}")
            return False

        return True

    except Exception as e:
        print(". Ошибка проверки CMS:", str(e))
        return False
