import { constructWebhookEvent, type DocumentEventData, WebhookVerificationError } from "@tupana-ai/sdk";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

/** POST /api/webhooks/tupana — recibe los eventos de Tupana con la firma verificada. */
export async function POST(request: Request) {
  // Cuerpo CRUDO: la firma se calcula sobre los bytes exactos.
  const payload = await request.text();
  try {
    const event = await constructWebhookEvent<DocumentEventData>(
      payload,
      request.headers,
      process.env.TUPANA_WEBHOOK_SECRET!,
    );
    // Deduplica con request.headers.get("x-pana-event-id") en tu base de datos.
    if (event.event === "document.issued") {
      console.log(`Factura emitida: folio ${event.data.folio}, pedido ${event.data.json_param?.order_id}`);
    }
    return NextResponse.json({ ok: true });
  } catch (err) {
    if (err instanceof WebhookVerificationError) {
      return NextResponse.json({ error: err.message }, { status: 400 });
    }
    throw err;
  }
}
