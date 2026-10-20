import { APIError } from "@tupana-ai/sdk";
import { NextResponse } from "next/server";
import { getTupana } from "@/lib/tupana";

export const runtime = "nodejs";

/** GET /api/invoices/{batchId} — estado de la emisión, folio y PDF. */
export async function GET(_request: Request, { params }: { params: Promise<{ batchId: string }> }) {
  const { batchId } = await params;
  try {
    const batch = await getTupana().documents.retrieveBatch(batchId);
    const doc = batch.documents[0];
    return NextResponse.json({
      status: batch.status,
      documentStatus: doc?.status ?? null,
      folio: doc?.document?.folio ?? null,
      pdfUrl: doc?.document?.pdf_url ?? null,
      total: doc?.document?.document_total?.total_amount ?? null,
    });
  } catch (err) {
    if (err instanceof APIError) {
      return NextResponse.json({ error: err.message, code: err.code }, { status: err.status });
    }
    throw err;
  }
}
