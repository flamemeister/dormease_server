import { useState } from "react";

export const ContractSigner = () => {
  const [status, setStatus] = useState("⌛ Ожидание...");
  const [signedXml, setSignedXml] = useState<string | null>(null);
  const [rawResponse, setRawResponse] = useState<string | null>(null); // 👈 для отладки

  const handleSign = () => {
    setStatus("🔌 Подключение к NCALayer...");
    setSignedXml(null);
    setRawResponse(null);

    const ws = new WebSocket("wss://127.0.0.1:13579/");
    ws.onopen = () => {
      const xmlData = `<?xml version="1.0" encoding="UTF-8"?>
<root>
  <contract>
    <studentName>Иванов Иван</studentName>
    <text>Бұл келісімшартқа қол қою үшін XML құжаты</text>
  </contract>
</root>`;

      const request = {
        module: "kz.gov.pki.knca.commonUtils",
        method: "signXml",
        args: [xmlData, "", "SIGNATURE"],
      };

      ws.send(JSON.stringify(request));
      setStatus("📤 XML отправлен на подписание...");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("📩 Ответ от NCALayer:", data);
        setRawResponse(JSON.stringify(data, null, 2));

        if (data.errorCode) {
          setStatus("❌ Подпись не удалась: " + data.errorCode);
          return;
        }

        if (!data.result || typeof data.result !== "string") {
          setStatus("❌ Получен пустой или некорректный результат.");
          return;
        }

        setSignedXml(data.result);
        setStatus("✅ Подпись получена успешно!");
      } catch (e) {
        setStatus("❌ Ошибка при обработке ответа.");
        console.error("Ошибка парсинга:", e);
      }
    };

    ws.onerror = () => {
      setStatus("❌ Ошибка подключения к NCALayer.");
    };
  };

  const handleDownload = () => {
    if (!signedXml) return;
    const blob = new Blob([signedXml], { type: "application/xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "signed_contract.xml";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ padding: 20, maxWidth: 800 }}>
      <h2>📄 Подписание XML через NCALayer</h2>
      <p><strong>Статус:</strong> {status}</p>
      <button onClick={handleSign} style={{ padding: "0.5rem 1rem", marginTop: 10 }}>
        🔏 Подписать XML
      </button>

      {signedXml && (
        <>
          <p style={{ marginTop: 20 }}>📄 Подписанный XML:</p>
          <textarea
            style={{ width: "100%", height: 300 }}
            readOnly
            value={signedXml}
          />
          <br />
          <button onClick={handleDownload} style={{ padding: "0.5rem 1rem", marginTop: 10 }}>
            📥 Скачать подписанный XML
          </button>
        </>
      )}

      {!signedXml && rawResponse && (
        <>
          <p style={{ marginTop: 20, color: "gray" }}>📜 Ответ от NCALayer:</p>
          <pre style={{ backgroundColor: "#f5f5f5", padding: 10 }}>
            {rawResponse}
          </pre>
        </>
      )}
    </div>
  );
};
