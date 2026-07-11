import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DocSprint — AI Document Processing",
  description:
    "Upload documents and get structured JSON from AI vision-language models.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0a0a0b] text-[#e4e4e7] antialiased">
        {children}
      </body>
    </html>
  );
}