'use client'

import { useEffect, useState } from 'react'
import { Loader2, LogIn, ShieldHalf, UserPlus, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { login, register } from '@/lib/api'
import { useToast } from '@/components/toast'

export function openAuth(): void {
  window.dispatchEvent(new Event('vyoma:open-auth'))
}

export function AuthModal({ onUserChange }: { onUserChange: () => void }) {
  const toast = useToast()
  const [open, setOpen] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState<'login' | 'register' | null>(null)

  useEffect(() => {
    const handler = () => setOpen(true)
    window.addEventListener('vyoma:open-auth', handler)
    return () => window.removeEventListener('vyoma:open-auth', handler)
  }, [])

  if (!open) return null

  const close = () => {
    if (!busy) setOpen(false)
  }

  const signIn = async () => {
    if (busy || !username || !password) {
      toast.push({ kind: 'warning', title: 'Missing credentials', message: 'Enter a username and password.' })
      return
    }
    setBusy('login')
    try {
      await login(username, password)
      toast.push({ kind: 'success', title: 'Signed in', message: `Authenticated as ${username}.` })
      onUserChange()
      setOpen(false)
    } catch (error) {
      toast.push({
        kind: 'error',
        title: 'Sign-in failed',
        message: error instanceof Error ? error.message : 'Invalid username or password.',
      })
    } finally {
      setBusy(null)
    }
  }

  const signUp = async () => {
    if (busy || !username || !password) {
      toast.push({ kind: 'warning', title: 'Missing credentials', message: 'Enter a username and password.' })
      return
    }
    setBusy('register')
    try {
      await register(username, password)
      await login(username, password)
      toast.push({ kind: 'success', title: 'Account created', message: `Registered and signed in as ${username}.` })
      onUserChange()
      setOpen(false)
    } catch (error) {
      toast.push({
        kind: 'error',
        title: 'Registration failed',
        message: error instanceof Error ? error.message : 'Could not create the account.',
      })
    } finally {
      setBusy(null)
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-[90] bg-black/70" onClick={close} aria-hidden />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Sign in"
        className="fixed left-1/2 top-1/2 z-[100] w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border border-border bg-card p-6 shadow-2xl"
      >
        <button
          onClick={close}
          className="absolute right-4 top-4 rounded p-1 text-muted-foreground transition-colors hover:text-foreground"
          aria-label="Close"
        >
          <X className="size-5" />
        </button>

        <div className="mb-5 flex items-center gap-3">
          <span className="flex size-11 items-center justify-center rounded bg-primary/15 ring-1 ring-primary/40">
            <ShieldHalf className="size-6 text-primary" />
          </span>
          <div>
            <h3 className="font-mono text-sm font-bold tracking-widest text-foreground">VYOMA KAVACH</h3>
            <p className="text-xs text-muted-foreground">Sign in to the local safety backend</p>
          </div>
        </div>

        <label htmlFor="auth-username" className="mb-1 block text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Username
        </label>
        <input
          id="auth-username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          className="mb-4 w-full rounded-md border border-border bg-background/60 px-3 py-2.5 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-1 focus:ring-primary"
          placeholder="officer"
        />

        <label htmlFor="auth-password" className="mb-1 block text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Password
        </label>
        <input
          id="auth-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && signIn()}
          autoComplete="current-password"
          className="mb-5 w-full rounded-md border border-border bg-background/60 px-3 py-2.5 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-1 focus:ring-primary"
          placeholder="••••••••"
        />

        <div className="flex gap-3">
          <button
            onClick={signIn}
            disabled={busy !== null}
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-60"
          >
            {busy === 'login' ? <Loader2 className="size-4 animate-spin" /> : <LogIn className="size-4" />}
            Sign In
          </button>
          <button
            onClick={signUp}
            disabled={busy !== null}
            className={cn(
              'inline-flex flex-1 items-center justify-center gap-2 rounded-md border px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-60',
              'border-border bg-secondary text-foreground hover:bg-accent',
            )}
          >
            {busy === 'register' ? <Loader2 className="size-4 animate-spin" /> : <UserPlus className="size-4" />}
            Create Account
          </button>
        </div>

        <p className="mt-4 text-[11px] leading-relaxed text-muted-foreground">
          Accounts live in the local backend only. New accounts are standard users; officer
          clearance is granted server-side.
        </p>
      </div>
    </>
  )
}