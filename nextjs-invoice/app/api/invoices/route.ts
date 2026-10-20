import { APIError, type DocumentInput } from "tupana";
import { NextResponse } from "next/server";
import { getTupana } from "@/lib/tupana";

export const runtime = "nodejs";

interface InvoiceRequest {
  /** Id de tu pedido: se usa como Idempotency-Key, así un doble clic no emite dos facturas. */
  orderId: string;
  receiverRut: string;
  items: Array<{ name: string; quantity: number; unitPrice: number }>;
}

const RUT = /^[0-9]{7,8}-[0-9Kk]$/;

function validate(body: Partial<InvoiceRequest>): string | null {
  if (!body.orderId) return "Falta orderId";
  if (!body.receiverRut || !RUT.test(body.receiverRut)) return "RUT del receptor inválido (ej. 76123456-0)";
  if (!Array.isArray(body.items) || body.items.length === 0) return "Agrega al menos un ítem";
  for (const it of body.items) {
    if (!it.name || !(it.quantity > 0) || !(it.unitPrice >= 0)) return "Ítem inválido";
  }
  return null;
}

/**
 * POST /api/invoices — emite una factura electrónica (DTE 33).
 *
 * IMPORTANTE: protege esta ruta con la autenticación de tu app antes de usarla en producción.
 */
export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as Partial<InvoiceRequest>;
  const error = validate(body);
  if (error) return NextResponse.json({ error }, { status: 400 });

  const invoice: DocumentInput = {
    dte_type: { code: "33" },
    document_issuer: { rut: process.env.TUPANA_ISSUER_RUT! },
    document_receiver: { rut: body.receiverRut!.toUpperCase() },
    details: body.items!.map((it) => ({
      item_name: it.name,
      quantity: it.quantity,
      unit_price: it.unitPrice,
    })),
    json_param: { order_id: body.orderId },
  };

  try {
    const batch = await getTupana().documents.createBatch(
      { documents: [invoice] },
      { useDefaults: true, idempotencyKey: `order-${body.orderId}` },
    );
    // La emisión al SII sigue en segundo plano: el cliente consulta /api/invoices/{batchId}
    // o tu backend espera el webhook document.issued.
    return NextResponse.json({ batchId: batch.batch_id, status: batch.status }, { status: 202 });
  } catch (err) {
    if (err instanceof APIError) {
      return NextResponse.json(
        { error: err.message, code: err.code, param: err.param, requestId: err.requestId },
        { status: err.status >= 500 ? 502 : err.status },
      );
    }
    throw err;
  }
}
