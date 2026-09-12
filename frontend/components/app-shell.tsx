'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useToast } from '@/components/toast'
import {
  LayoutDashboard,
  FilePlus2,
  Activity,
  Gavel,
  Map,
  ShieldHalf,
  ScrollText,
  FileDown,
  Settings,
  PanelLeftClose,
  PanelLeft,
  Bell,
  ChevronDown,
  LogIn,
  LogOut,
  User,
  BadgeCheck,
  Menu,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { StatusDot } from '@/components/status-badge'
import { getCurrentUser, getHealth, getSecurityStatus, isAuthed, logout } from '@/lib/api'
import { AuthModal, openAuth } from '@/components/auth-modal'
import type { LucideIcon } from 'lucide-react'

const sections: { label: string; items: { href: string; label: string; icon: LucideIcon }[] }[] = [
  {
    label: 'Overview',
    items: [{ href: '/', label: 'Overview', icon: LayoutDashboard }],
  },
  {
    label: 'AI WORKBENCH',
    items: [{ href: '/workbench', label: 'AI Workspace', icon: Settings }],
  },
  {
    label: 'INDUSTRIAL APPS · KAVACH',
    items: [
      { href: '/new-inspection', label: 'PTW Analysis', icon: FilePlus2 },
      { href: '/processing', label: 'Processing', icon: Activity },
      { href: '/verdict', label: 'Safety Review', icon: Gavel },
      { href: '/annotated', label: 'Annotated P&ID', icon: Map },
      { href: '/deliverables', label: 'Deliverables', icon: FileDown },
    ],
  },
  {
    label: 'GOVERNANCE',
    items: [
      { href: '/security', label: 'Security', icon: ShieldHalf },
      { href: '/audit', label: 'Audit Trail', icon: ScrollText },
    ],
  },
]

const sectionTitles: Record<string, string> = {
  '/': 'Overview',
  '/new-inspection': 'PTW Analysis',
  '/processing': 'Processing Monitor',
  '/verdict': 'Safety Review',
  '/annotated': 'Annotated P&ID',
  '/security': 'Security Operations',
  '/audit': 'Audit Trail',
  '/workbench': 'AI Workspace',
  '/deliverables': 'Deliverables',
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const toast = useToast()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [userMenu, setUserMenu] = useState(false)
  const [user, setUser] = useState<string | null>(null)
  const [apiUp, setApiUp] = useState<boolean | null>(null)
  const [egressActive, setEgressActive] = useState<boolean | null>(null)

  const refreshUser = () => setUser(getCurrentUser())

  useEffect(() => {
    refreshUser()
    getHealth()
      .then(() => setApiUp(true))
      .catch(() => setApiUp(false))
    getSecurityStatus()
      .then((s) => setEgressActive(s.external_observed_since_start === 0))
      .catch(() => setEgressActive(null))
  }, [])

  const signOut = () => {
    logout()
    setUserMenu(false)
    refreshUser()
    toast.push({ kind: 'info', title: 'Signed out', message: 'Local session cleared.' })
  }

  const section = sectionTitles[pathname] ?? 'VYOMA'
  const apiConnected = apiUp === true
  const apiKnown = apiUp !== null

  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex flex-col border-r border-sidebar-border bg-sidebar transition-all duration-300 lg:static',
          collapsed ? 'w-[68px]' : 'w-64',
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-sidebar-border px-4">
          <div className="relative flex size-9 shrink-0 items-center justify-center rounded bg-primary/15 ring-1 ring-primary/40">
            <ShieldHalf className="size-5 text-primary" />
            <span className="absolute inset-0 rounded ring-1 ring-primary/20 animate-status-pulse" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <p className="truncate font-mono text-sm font-bold tracking-widest text-foreground">
                VYOMA
              </p>
              <p className="truncate text-[10px] uppercase tracking-wider text-muted-foreground">
                KAVACH · Industrial Safety Intelligence
              </p>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          {sections.map((section) => (
            <div key={section.label} className="mb-4 last:mb-0">
              {!collapsed && (
                <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                  {section.label}
                </p>
              )}
              <div className="space-y-1">
                {section.items.map((item) => {
                  const active = pathname === item.href
                  const Icon = item.icon
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setMobileOpen(false)}
                      title={collapsed ? item.label : undefined}
                      className={cn(
                        'group relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                        active
                          ? 'bg-sidebar-accent text-foreground'
                          : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground',
                      )}
                    >
                      {active && (
                        <span className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-primary" />
                      )}
                      <Icon className={cn('size-5 shrink-0', active && 'text-primary')} />
                      {!collapsed && <span className="truncate">{item.label}</span>}
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* System status */}
        {!collapsed && (
          <div className="mx-3 mb-3 rounded-md border border-sidebar-border bg-background/40 p-3">
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
              System Status
            </p>
            <div className="space-y-1.5 text-xs">
              <div className="flex items-center gap-2 text-foreground">
                <StatusDot tone={apiUp === false ? 'danger' : 'safe'} pulse={!apiKnown} />
                Backend {apiConnected ? 'Connected' : apiKnown ? 'OFFLINE' : 'Connecting'}
              </div>
              <div className="flex items-center gap-2 text-foreground">
                <StatusDot tone={egressActive === false ? 'danger' : 'safe'} pulse={egressActive === null} />
                {egressActive === null
                  ? 'Egress status…'
                  : egressActive
                    ? 'Zero-Egress Active'
                    : 'Egress Observed'}
              </div>
            </div>
          </div>
        )}

        {/* User profile */}
        <div className="flex items-center gap-3 border-t border-sidebar-border px-4 py-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-secondary font-mono text-xs font-bold text-foreground">
            {user ? user.slice(0, 2).toUpperCase() : '–'}
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-foreground">
                {user ? 'Safety Officer' : 'Not signed in'}
              </p>
              <p className="truncate font-mono text-[11px] text-muted-foreground">
                {user ? user.toUpperCase() : 'Sign in to continue'}
              </p>
            </div>
          )}
        </div>
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden
        />
      )}

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b border-border bg-background/85 px-4 backdrop-blur">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileOpen(true)}
              className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground lg:hidden"
              aria-label="Open navigation"
            >
              <Menu className="size-5" />
            </button>
            <button
              onClick={() => setCollapsed((c) => !c)}
              className="hidden rounded-md p-2 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground lg:block"
              aria-label="Toggle sidebar"
            >
              {collapsed ? <PanelLeft className="size-5" /> : <PanelLeftClose className="size-5" />}
            </button>
            <div>
              <h1 className="text-sm font-semibold text-foreground sm:text-base">{section}</h1>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-4">
            <div className="hidden items-center gap-3 md:flex">
              <span
                className={cn(
                  'flex items-center gap-2 rounded border px-2.5 py-1 font-mono text-[11px]',
                  apiConnected
                    ? 'border-safe/25 bg-safe/10 text-safe'
                    : 'border-danger/25 bg-danger/10 text-danger',
                )}
              >
                <StatusDot tone={apiConnected ? 'safe' : 'danger'} />
                {apiConnected ? 'API CONNECTED' : apiKnown ? 'API OFFLINE' : 'CONNECTING'}
              </span>
              <span className="flex items-center gap-2 rounded border border-info/25 bg-info/10 px-2.5 py-1 font-mono text-[11px] text-info">
                <StatusDot tone="info" /> ZERO-EGRESS
              </span>
            </div>

            <button
              className="relative rounded-md p-2 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              aria-label="Notifications"
            >
              <Bell className="size-5" />
              <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-warning ring-2 ring-background" />
            </button>

            <div className="relative">
              <button
                onClick={() => setUserMenu((v) => !v)}
                className="flex items-center gap-2 rounded-md p-1 pr-2 transition-colors hover:bg-secondary"
                aria-haspopup="menu"
                aria-expanded={userMenu}
              >
                <span className="flex size-8 items-center justify-center rounded-full bg-primary/15 font-mono text-xs font-bold text-primary ring-1 ring-primary/30">
                  {user ? user.slice(0, 2).toUpperCase() : '–'}
                </span>
                <span className="hidden text-sm font-medium text-foreground sm:block">
                  {user ?? 'Sign In'}
                </span>
                <ChevronDown className="size-4 text-muted-foreground" />
              </button>
              {userMenu && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setUserMenu(false)} aria-hidden />
                  <div
                    role="menu"
                    className="absolute right-0 z-50 mt-2 w-52 overflow-hidden rounded-md border border-border bg-card-elevated py-1 shadow-xl"
                  >
                    {user ? (
                      <>
                        <div className="border-b border-border px-3 py-2">
                          <p className="text-sm font-medium text-foreground">Safety Officer</p>
                          <p className="font-mono text-xs text-muted-foreground">
                            {user.toUpperCase()}
                          </p>
                        </div>
                        <button className="flex w-full items-center gap-2 px-3 py-2 text-sm text-foreground transition-colors hover:bg-secondary">
                          <User className="size-4 text-muted-foreground" /> Profile
                        </button>
                        <button className="flex w-full items-center gap-2 px-3 py-2 text-sm text-foreground transition-colors hover:bg-secondary">
                          <BadgeCheck className="size-4 text-muted-foreground" /> Role &amp; Clearance
                        </button>
                        <button
                          onClick={signOut}
                          className="flex w-full items-center gap-2 px-3 py-2 text-sm text-danger transition-colors hover:bg-danger/10"
                        >
                          <LogOut className="size-4" /> Logout
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => {
                          setUserMenu(false)
                          openAuth()
                        }}
                        className="flex w-full items-center gap-2 px-3 py-2 text-sm text-foreground transition-colors hover:bg-secondary"
                      >
                        <LogIn className="size-4 text-muted-foreground" /> Sign In
                      </button>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        <main className="flex-1">{children}</main>
      </div>
      <AuthModal onUserChange={refreshUser} />
    </div>
  )
}