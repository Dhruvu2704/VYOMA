import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'
import { Panel, PanelHeader } from '@/components/panel'
import { StatusBadge } from '@/components/status-badge'
import type { ActiveTask } from '@/lib/mock-data'

export function ActiveTasksTable({ tasks }: { tasks: ActiveTask[] }) {
  return (
    <Panel corners>
      <PanelHeader
        title="Active Tasks"
        action={
          <Link
            href="/audit"
            className="flex items-center gap-1 text-xs font-medium text-primary transition-colors hover:text-primary/80"
          >
            View all <ArrowUpRight className="size-3.5" />
          </Link>
        }
      />
      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] text-sm">
          <thead>
            <tr className="border-b border-border text-left text-[10px] uppercase tracking-widest text-muted-foreground">
              <th className="px-4 py-2.5 font-semibold">Task ID</th>
              <th className="px-4 py-2.5 font-semibold">Permit ID</th>
              <th className="px-4 py-2.5 font-semibold">Asset</th>
              <th className="px-4 py-2.5 font-semibold">Status</th>
              <th className="px-4 py-2.5 font-semibold">Rule</th>
              <th className="px-4 py-2.5 font-semibold">LLM</th>
              <th className="px-4 py-2.5 font-semibold">Agreement</th>
              <th className="px-4 py-2.5 text-right font-semibold">Updated</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr
                key={t.taskId}
                className="border-b border-border/60 transition-colors last:border-0 hover:bg-secondary/40"
              >
                <td className="px-4 py-3">
                  <Link
                    href="/verdict"
                    className="font-mono text-xs text-primary transition-colors hover:text-primary/80"
                  >
                    {t.taskId}
                  </Link>
                </td>
                <td className="px-4 py-3 font-mono text-xs text-foreground">{t.permitId}</td>
                <td className="px-4 py-3 text-foreground">{t.asset}</td>
                <td className="px-4 py-3">
                  <StatusBadge value={t.status} size="sm" />
                </td>
                <td className="px-4 py-3">
                  <StatusBadge value={t.ruleResult} size="sm" />
                </td>
                <td className="px-4 py-3">
                  <StatusBadge value={t.llmResult} size="sm" />
                </td>
                <td className="px-4 py-3">
                  <StatusBadge value={t.agreement} size="sm" />
                </td>
                <td className="px-4 py-3 text-right font-mono text-xs text-muted-foreground">
                  {t.updated}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}
