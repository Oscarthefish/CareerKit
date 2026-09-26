import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'CareerKit Local',
  description: 'Private job application assistant',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
