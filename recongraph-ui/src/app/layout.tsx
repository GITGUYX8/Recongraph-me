import type { Metadata } from "next";
import { Playfair_Display, Space_Grotesk, Space_Mono } from "next/font/google";
import Script from "next/script";
import "./globals.css";

const playfair = Playfair_Display({
  variable: "--font-playfair",
  subsets: ["latin"],
  weight: ["400", "700"],
  style: ["normal", "italic"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
});

const spaceMono = Space_Mono({
  variable: "--font-space-mono",
const spaceMono = Space_Mono({
  variable: "--font-space-mono",
  subsets: ["latin"],
  weight: ["400", "700"],
  weight: ["400", "700"],
});

export const metadata: Metadata = {
  title: "ReconGraph | Financial Reconciliation & Investigation",
  description: "AI-assisted financial reconciliation and investigation platform.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <Script src="https://code.iconify.design/iconify-icon/1.0.7/iconify-icon.min.js" strategy="beforeInteractive" />
      </head>
      <body
        className={`${playfair.variable} ${spaceGrotesk.variable} ${spaceMono.variable} antialiased min-h-screen`}
      >
        {children}
      </body>
    </html>
  );
}
