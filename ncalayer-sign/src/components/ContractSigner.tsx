import { useState } from "react";
import Client from "@seithq/ncalayer";

// 🔧 Безопасная base64-кодировка для Unicode-строк (рус/каз символов)
function base64EncodeUnicode(str: string): string {
  return btoa(unescape(encodeURIComponent(str)));
}

export const ContractSigner = () => {
  const [status, setStatus] = useState("⌛ Ожидание...");
  const [signature, setSignature] = useState<string | null>(null);

  const handleSign = () => {
    setStatus("🔌 Подключение к NCALayer...");

    const ws = new WebSocket("wss://127.0.0.1:13579/");
    ws.onopen = () => {
      const client = new Client(ws);

      // 👉 Текст для подписи
      const plainText = "Бұл ЭЦП арқылы қол қоюға арналған тесттік мәтін";
      const dataToSign = base64EncodeUnicode(plainText);

      // 📂 Шаг 1 — выбрать P12-файл
      client.browseKeyStore("PKCS12", "P12", "", (res1) => {
        console.log("📂 browseKeyStore result:", res1);

        if (!res1.isOk()) {
          setStatus("❌ Не удалось выбрать ключевой файл");
          return;
        }

        const storagePath = res1.getResult();
        const password = prompt("🔐 Введите пароль от ключа") || "";

        const keyAlias = ""; // ⚠️ Пусть NCALayer сам подставит alias

        setStatus("🔏 Подписание...");

        // ✍️ Подписываем данные
        client.signPlainData(
          "PKCS12",
          storagePath,
          keyAlias,
          password,
          dataToSign,
          (res2) => {
            console.log("✍️ signPlainData result:", res2);

            if (!res2.isOk()) {
              console.error("❌ Ошибка при подписи:", res2.getErrorMessage?.() || res2);
              setStatus("❌ Подпись не удалась. Возможно, неверный пароль или неподходящий ключ.");
              return;
            }

            const sig = res2.getResult();
            setSignature(sig);
            setStatus("✅ Подпись успешно получена!");

            // 👇 Пример отправки на сервер
            /*
            fetch("/api/verify", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ data: dataToSign, signature: sig }),
            });
            */
          }
        );
      });
    };

    ws.onerror = () => {
      setStatus("❌ NCALayer не отвечает. Убедитесь, что он запущен.");
    };
  };

  return (
    <div style={{ padding: 20, maxWidth: 600 }}>
      <h2>📑 Подписание строки через NCALayer</h2>
      <p><strong>Статус:</strong> {status}</p>
      <button onClick={handleSign} style={{ padding: "0.5rem 1rem", marginTop: 10 }}>
        🔏 Подписать строку
      </button>

      {signature && (
        <>
          <p style={{ marginTop: 20 }}>📄 Подпись (base64):</p>
          <textarea
            style={{ width: "100%", height: 160 }}
            readOnly
            value={signature}
          />
        </>
      )}
    </div>
  );
};
