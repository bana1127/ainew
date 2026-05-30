import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ClubAgent",
  description: "ClubAgent admin dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}

