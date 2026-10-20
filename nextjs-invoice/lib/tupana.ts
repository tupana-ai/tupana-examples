import "server-only";
import Tupana from "tupana";

let client: Tupana | undefined;

/**
 * Un solo cliente por proceso, creado al primer uso (así `next build` no exige la key).
 * Solo en el servidor: la API key nunca llega al navegador.
 */
export function getTupana(): Tupana {
  client ??= new Tupana({ apiKey: process.env.TUPANA_API_KEY });
  return client;
}
