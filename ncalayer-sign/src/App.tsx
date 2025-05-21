import { ContractSigner } from "./components/ContractSigner";

function App() {
  return (
    <div style={{ padding: "2rem" }}>
      <h1>Договор</h1>
      <ContractSigner appId={4} /> {/* Заменить на нужный appId */}
    </div>
  );
}

export default App;
