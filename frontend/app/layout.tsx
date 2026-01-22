import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'KSA RegTech',
  description: 'KSA RegTech',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
