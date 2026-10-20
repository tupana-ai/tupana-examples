"use client";

import { type FormEvent, useState } from "react";

type Result = { status: string; folio: string | null; pdfUrl: string | null; total: number | null };

export default function Page() {
  const [state, setState] = useState<"idle" | "sending" | "waiting" | "done" | "error">("idle");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<Result | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setState("sending");
    setResult(null);
    const res = await fetch("/api/invoices", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        orderId: form.get("orderId"),
        receiverRut: form.get("receiverRut"),
        items: [{ name: form.get("item"), quantity: Number(form.get("quantity")), unitPrice: Number(form.get("unitPrice")) }],
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      setState("error");
      setMessage(data.error ?? "No se pudo emitir");
      return;
    }
    setState("waiting");
    for (let i = 0; i < 60; i++) {
      await new Promise((r) => setTimeout(r, 2000));
      const status: Result = await (await fetch(`/api/invoices/${data.batchId}`)).json();
      if (status.status === "completed" || status.status === "failed") {
        setResult(status);
        setState(status.status === "completed" ? "done" : "error");
        setMessage(status.status === "failed" ? "El SII no aceptó el documento" : "");
        return;
      }
    }
    setState("error");
    setMessage("La emisión sigue en curso; revisa más tarde.");
  }

  return (
    <main>
      <h1>Emitir factura</h1>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: 8 }}>
        <input name="orderId" placeholder="N° de pedido" defaultValue={`PED-${Date.now()}`} required />
        <input name="receiverRut" placeholder="RUT del cliente (76123456-0)" required />
        <input name="item" placeholder="Descripción" defaultValue="Asesoría" required />
        <input name="quantity" type="number" min="1" defaultValue="1" required />
        <input name="unitPrice" type="number" min="0" placeholder="Precio neto" required />
        <button type="submit" disabled={state === "sending" || state === "waiting"}>
          {state === "waiting" ? "Emitiendo en el SII…" : "Emitir"}
        </button>
      </form>
      {message && <p role="alert">{message}</p>}
      {result?.folio && (
        <p>
          Factura folio <strong>{result.folio}</strong>
          {result.total != null && ` por $${result.total.toLocaleString("es-CL")}`}.{" "}
          {result.pdfUrl && <a href={result.pdfUrl} target="_blank" rel="noreferrer">Ver PDF</a>}
        </p>
      )}
    </main>
  );
}
