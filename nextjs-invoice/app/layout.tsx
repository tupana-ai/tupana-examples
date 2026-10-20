import type { ReactNode } from "react";

export const metadata = { title: "Factura con Tupana" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es-CL">
      <body style={{ fontFamily: "system-ui, sans-serif", maxWidth: 560, margin: "40px auto", padding: "0 16px" }}>
        {children}
      </body>
    </html>
  );
}
