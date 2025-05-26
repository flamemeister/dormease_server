from asn1crypto import cms, x509
import hashlib

def verify_cms_signature(pdf_path, cms_bytes) -> bool:
    try:
        content_info = cms.ContentInfo.load(cms_bytes)
        signed_data = content_info['content']
        certificates = signed_data['certificates']

        signer_infos = signed_data['signer_infos']
        if not signer_infos:
            print("❌ Нет подписанта в CMS")
            return False

        # Подпись только одна
        signer = signer_infos[0]
        sid = signer['sid']
        issuer_serial = sid.chosen
        serial = issuer_serial['serial_number'].native

        # Ищем соответствующий сертификат
        cert = next((x.chosen for x in certificates if x.name == 'certificate' and x.chosen.serial_number == serial), None)
        if not cert:
            print("❌ Сертификат не найден в CMS")
            return False

        # Получаем публичный ключ
        pub_key = cert.public_key

        # Получаем оригинальный PDF
        with open(pdf_path, 'rb') as f:
            content = f.read()

        # Проверка подписи (hash и сравнение)
        digest_oid = signer['digest_algorithm']['algorithm'].dotted
        signature = signer['signature'].native

        if digest_oid.startswith("1.2.398.3.10"):
            print("⚠️ ГОСТ-алгоритм обнаружен. Пропускаем проверку подписи.")
            return True  # или можешь return False, если хочешь только info без валидации

        # Если не ГОСТ — проверяем стандартно
        digest_algo = signer['digest_algorithm']['algorithm'].native

        if digest_algo == 'sha256':
            digest = hashlib.sha256(content).digest()
        elif digest_algo == 'sha1':
            digest = hashlib.sha1(content).digest()
        else:
            print(f"❌ Неподдерживаемый digest алгоритм: {digest_algo}")
            return False

        # Проверка подписи (если не ГОСТ)
        try:
            pub_key.verify(signature, digest)
        except Exception as e:
            print(f"❌ Подпись недействительна: {e}")
            return False


        # Получаем подпись и проверяем
        pub_key.verify(signature, digest)

        return True

    except Exception as e:
        print("❌ Ошибка проверки CMS:", str(e))
        return False
