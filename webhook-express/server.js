import { createApp } from "./app.js";

const port = Number(process.env.PORT ?? 3000);
createApp({ secret: process.env.TUPANA_WEBHOOK_SECRET }).listen(port, () => {
  console.log(`Escuchando webhooks de Tupana en http://localhost:${port}/webhooks/tupana`);
});
