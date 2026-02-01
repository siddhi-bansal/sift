import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sift — Signal, not noise. Build what matters.",
  description: "Sift scans developer conversations and tech news, then distills real, repeated problems into clear, evidence-backed signals and buildable opportunities. For founders and developers.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
