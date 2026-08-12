"use client";

import { useEffect, useState, useCallback } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Ticket {
  ref_id: string;
  caller_name: string;
  caller_language: string;
  preferred_follow_up: string;
  issue_type: string;
  what_happened: string;
  what_agent_checked: string;
  urgency: "low" | "medium" | "high" | "emergency";
  status: "open" | "in_progress" | "resolved";
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

interface Stats {
  total: number;
  by_status: { open: number; in_progress: number; resolved: number };
  by_urgency: { emergency: number; high: number; medium: number; low: number };
}

// ─── Config ───────────────────────────────────────────────────────────────────

const API_BASE = "http://localhost:8001/api";

// ─── Helpers ─────────────────────────────────────────────────────────────────

const URGENCY_STYLES: Record<string, string> = {
  emergency: "bg-red-500/20 text-red-300 border border-red-500/40",
  high:      "bg-orange-500/20 text-orange-300 border border-orange-500/40",
  medium:    "bg-yellow-500/20 text-yellow-300 border border-yellow-500/40",
  low:       "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40",
};

const STATUS_STYLES: Record<string, string> = {
  open:        "bg-blue-500/20 text-blue-300 border border-blue-500/40",
  in_progress: "bg-purple-500/20 text-purple-300 border border-purple-500/40",
  resolved:    "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40",
};

const ISSUE_LABELS: Record<string, string> = {
  payment_refund:  "💳 Payment / Refund",
  order_complaint: "📦 Order Complaint",
  other:           "❓ Other",
};

const FOLLOW_UP_ICONS: Record<string, string> = {
  call:      "📞",
  email:     "✉️",
  sms:       "💬",
  whatsapp:  "🟢",
};

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function Badge({ label, style }: { label: string; style: string }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold tracking-wide ${style}`}>
      {label}
    </span>
  );
}

// ─── Stat Card ────────────────────────────────────────────────────────────────

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className={`rounded-2xl p-5 border ${color} flex flex-col gap-1 min-w-[120px]`}>
      <span className="text-3xl font-bold">{value}</span>
      <span className="text-xs uppercase tracking-widest opacity-70">{label}</span>
    </div>
  );
}

// ─── Ticket Row ───────────────────────────────────────────────────────────────

function TicketRow({
  ticket,
  onStatusChange,
}: {
  ticket: Ticket;
  onStatusChange: (refId: string, newStatus: string, resolve: boolean) => Promise<void>;
}) {
  const [loading, setLoading] = useState(false);

  const handleStatusChange = async (newStatus: string, isResolve = false) => {
    setLoading(true);
    await onStatusChange(ticket.ref_id, newStatus, isResolve);
    setLoading(false);
  };

  return (
    <tr className="border-b border-white/5 hover:bg-white/[0.03] transition-colors group">
      {/* Ref ID */}
      <td className="py-4 px-4">
        <span className="font-mono text-sm text-sky-300 font-semibold tracking-tight">
          {ticket.ref_id}
        </span>
      </td>

      {/* Caller */}
      <td className="py-4 px-4">
        <div className="font-medium text-white">{ticket.caller_name}</div>
        <div className="text-xs text-white/40 mt-0.5">
          {ticket.caller_language} &bull;{" "}
          {FOLLOW_UP_ICONS[ticket.preferred_follow_up] || "📞"} {ticket.preferred_follow_up}
        </div>
      </td>

      {/* Issue */}
      <td className="py-4 px-4 text-sm text-white/70">
        {ISSUE_LABELS[ticket.issue_type] || ticket.issue_type}
      </td>

      {/* Urgency */}
      <td className="py-4 px-4">
        <Badge
          label={ticket.urgency.toUpperCase()}
          style={URGENCY_STYLES[ticket.urgency] || "bg-white/10 text-white"}
        />
      </td>

      {/* Status */}
      <td className="py-4 px-4">
        <Badge
          label={ticket.status.replace("_", " ").toUpperCase()}
          style={STATUS_STYLES[ticket.status] || "bg-white/10 text-white"}
        />
      </td>

      {/* What Happened */}
      <td className="py-4 px-4 max-w-xs">
        <p className="text-sm text-white/60 line-clamp-2">{ticket.what_happened}</p>
        {ticket.what_agent_checked && (
          <p className="text-xs text-white/30 mt-0.5 line-clamp-1">
            Checked: {ticket.what_agent_checked}
          </p>
        )}
      </td>

      {/* Time */}
      <td className="py-4 px-4 text-xs text-white/40 whitespace-nowrap">
        {relativeTime(ticket.created_at)}
      </td>

      {/* Actions */}
      <td className="py-4 px-4">
        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          {ticket.status === "open" && (
            <button
              disabled={loading}
              onClick={() => handleStatusChange("in_progress")}
              className="px-3 py-1 text-xs rounded-lg bg-purple-600/30 hover:bg-purple-600/60 text-purple-200 border border-purple-500/30 transition-colors disabled:opacity-50"
            >
              Start Review
            </button>
          )}
          {ticket.status === "in_progress" && (
            <button
              disabled={loading}
              onClick={() => handleStatusChange("resolved", true)}
              className="px-3 py-1 text-xs rounded-lg bg-emerald-600/30 hover:bg-emerald-600/60 text-emerald-200 border border-emerald-500/30 transition-colors disabled:opacity-50"
            >
              ✓ Resolve &amp; Call Back
            </button>
          )}
          {ticket.status === "resolved" && (
            <span className="text-xs text-white/25 italic">Closed</span>
          )}
        </div>
      </td>
    </tr>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function EscalationDashboard() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchData = useCallback(async () => {
    try {
      const [ticketRes, statsRes] = await Promise.all([
        fetch(
          statusFilter === "all"
            ? `${API_BASE}/escalations`
            : `${API_BASE}/escalations?status=${statusFilter}`
        ),
        fetch(`${API_BASE}/escalations/stats`),
      ]);

      if (!ticketRes.ok || !statsRes.ok) {
        throw new Error("API request failed. Is the escalation server running on port 8001?");
      }

      const ticketData = await ticketRes.json();
      const statsData = await statsRes.json();

      setTickets(ticketData.tickets || []);
      setStats(statsData);
      setError(null);
      setLastRefresh(new Date());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  // Initial load + poll every 10 s
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10_000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleStatusChange = async (refId: string, newStatus: string, isResolve: boolean) => {
    const endpoint = isResolve
      ? `${API_BASE}/escalations/${refId}/resolve`
      : `${API_BASE}/escalations/${refId}/status`;
    const body = isResolve ? undefined : JSON.stringify({ status: newStatus });
    const method = "POST";
    const headers = { "Content-Type": "application/json" };

    await fetch(endpoint, { method, headers, body });
    await fetchData();
  };

  return (
    <div
      className="min-h-screen text-white"
      style={{ background: "linear-gradient(135deg, #0a0f1e 0%, #0d1a2e 50%, #0a0f1e 100%)" }}
    >
      {/* ── Header ── */}
      <div className="border-b border-white/10 px-8 py-5">
        <div className="max-w-[1400px] mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              🎧 Escalation Dashboard
            </h1>
            <p className="text-sm text-white/40 mt-0.5">
              Local Commerce Assistant &nbsp;·&nbsp; Human-in-the-Loop Support Tickets
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs text-white/40">
            <span>Auto-refreshes every 10s</span>
            <span className="opacity-60">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </span>
            <button
              onClick={fetchData}
              className="px-3 py-1.5 rounded-lg bg-sky-600/30 hover:bg-sky-600/50 text-sky-200 border border-sky-500/30 transition-colors text-xs"
            >
              ↻ Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-[1400px] mx-auto px-8 py-8 space-y-8">

        {/* ── Stats Row ── */}
        {stats && (
          <div className="flex flex-wrap gap-4">
            <StatCard label="Total" value={stats.total} color="border-white/10 text-white" />
            <StatCard label="Open" value={stats.by_status.open} color="border-blue-500/30 text-blue-300" />
            <StatCard label="In Progress" value={stats.by_status.in_progress} color="border-purple-500/30 text-purple-300" />
            <StatCard label="Resolved" value={stats.by_status.resolved} color="border-emerald-500/30 text-emerald-300" />
            <div className="flex-1" />
            <StatCard label="Emergency" value={stats.by_urgency.emergency} color="border-red-500/30 text-red-300" />
            <StatCard label="High" value={stats.by_urgency.high} color="border-orange-500/30 text-orange-300" />
            <StatCard label="Medium" value={stats.by_urgency.medium} color="border-yellow-500/30 text-yellow-300" />
            <StatCard label="Low" value={stats.by_urgency.low} color="border-emerald-500/30 text-emerald-300" />
          </div>
        )}

        {/* ── Filter Tabs ── */}
        <div className="flex gap-2">
          {["all", "open", "in_progress", "resolved"].map((f) => (
            <button
              key={f}
              onClick={() => setStatusFilter(f)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                statusFilter === f
                  ? "bg-sky-600 text-white shadow-lg shadow-sky-900/40"
                  : "bg-white/5 text-white/50 hover:bg-white/10 hover:text-white border border-white/10"
              }`}
            >
              {f === "all" ? "All Tickets" : f.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}
            </button>
          ))}
        </div>

        {/* ── Error ── */}
        {error && (
          <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-5 text-red-300 text-sm">
            <strong>⚠️ Connection Error:</strong> {error}
            <br />
            <span className="text-xs text-red-300/60 mt-1 block">
              Make sure the escalation API is running: <code className="bg-black/30 px-1 rounded">uv run uvicorn src.escalation_api:app --port 8001 --reload</code>
            </span>
          </div>
        )}

        {/* ── Table ── */}
        {!error && (
          <div className="rounded-2xl border border-white/10 overflow-hidden bg-white/[0.02] backdrop-blur-sm">
            {loading ? (
              <div className="flex items-center justify-center py-20 text-white/30 text-sm">
                Loading tickets…
              </div>
            ) : tickets.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 gap-3">
                <span className="text-5xl">🎉</span>
                <p className="text-white/40 text-sm">No escalation tickets found.</p>
                <p className="text-white/20 text-xs">A normal conversation without escalations is a good sign!</p>
              </div>
            ) : (
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-white/10 bg-white/[0.03]">
                    {["Ref ID", "Caller", "Issue Type", "Urgency", "Status", "Summary", "Created", "Actions"].map(
                      (h) => (
                        <th key={h} className="py-3 px-4 text-xs font-semibold text-white/40 uppercase tracking-widest">
                          {h}
                        </th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((t) => (
                    <TicketRow key={t.ref_id} ticket={t} onStatusChange={handleStatusChange} />
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* ── Legend ── */}
        <div className="flex flex-wrap gap-6 text-xs text-white/30">
          <div className="space-y-1">
            <p className="font-semibold text-white/50 uppercase tracking-wider">Urgency</p>
            {Object.entries(URGENCY_STYLES).map(([k, v]) => (
              <div key={k} className="flex items-center gap-2">
                <Badge label={k.toUpperCase()} style={v} />
                <span>
                  {k === "emergency" && "Large refund / very distressed caller"}
                  {k === "high" && "Payment dispute / damaged goods"}
                  {k === "medium" && "Wrong item / minor delay"}
                  {k === "low" && "General unresolved query"}
                </span>
              </div>
            ))}
          </div>
          <div className="space-y-1">
            <p className="font-semibold text-white/50 uppercase tracking-wider">Workflow</p>
            <p>Open → Start Review → Resolve &amp; Call Back</p>
            <p>Resolving triggers an outbound callback via Day 6 dial.py</p>
          </div>
        </div>
      </div>
    </div>
  );
}
