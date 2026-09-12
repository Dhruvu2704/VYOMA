import type { Metadata, Viewport } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { AppShell } from '@/components/app-shell'
import { ToastProvider } from '@/components/toast'
import './globals.css'

const geistSans = Geist({
  subsets: ['latin'],
  variable: '--font-geist-sans',
})

const geistMono = Geist_Mono({
  subsets: ['latin'],
  variable: '--font-geist-mono',
})

export const metadata: Metadata = {
  title: 'VYOMA — Sovereign Industrial AI Workbench',
  description:
    'VYOMA is a sovereign, on-premise industrial AI workbench. KAVACH, its flagship industrial app, delivers AI-verified Permit-to-Work and P&ID safety intelligence inside a zero-egress environment.',
}

export const viewport: Viewport = {
  colorScheme: 'dark',
  themeColor: '#111417',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`dark ${geistSans.variable} ${geistMono.variable}`}>
      <body className="bg-background font-sans antialiased">
        <ToastProvider>
          <AppShell>{children}</AppShell>
        </ToastProvider>
      </body>
    </html>
  )
}