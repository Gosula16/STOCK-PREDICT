"use client";

import { useCallback, useEffect, useState } from "react";

type Signal = {
  symbol: string;
  decision: string;
  confidence: number;
  rationale: string;
  last_price?: number | null;
};

type SignalsResponse = {
  trading_enabled?: boolean;
  signals?: Signal[];
  detail?: string;
};

type BrokerStatus = {
  groww_configured?: boolean;
  profile?: {
    ucc?: string;
    nse_enabled?: boolean;
    active_segments?: string[];
  } | null;
  instruments?: number;
  groww_allow_place_order?: boolean;
  broker_mode?: string;
  detail?: string;
};

function decisionStyle(d: string) {
  if (d === "BUY") return "text-emerald-400 bg-emerald-950/60 border-emerald-800";
  if (d === "SELL") return "text-rose-400 bg-rose-950/60 border-rose-800";
  return "text-amber-200 bg-amber-950/40 border-amber-800";
}

export default function Dashboard() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [tradingEnabled, setTradingEnabled] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [broker, setBroker] = useState<BrokerStatus | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch("/api/gateway/v1/signals", { cache: "no-store" });
      const j: SignalsResponse = await r.json();
      if (!r.ok) {
        setError(j.detail ?? `HTTP ${r.status}`);
        setSignals([]);
        return;
      }
      setSignals(j.signals ?? []);
      setTradingEnabled(j.trading_enabled ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
      setSignals([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshBroker = useCallback(async () => {
    try {
      const r = await fetch("/api/gateway/v1/broker/status", { cache: "no-store" });
      const j: BrokerStatus = await r.json();
      if (r.ok) setBroker(j);
      else setBroker(null);
    } catch {
      setBroker(null);
    }
  }, []);

  useEffect(() => {
    void refresh();
    void refreshBroker();
  }, [refresh, refreshBroker]);

  const toggleTrading = async (enabled: boolean) => {
    setActionBusy(true);
    setError(null);
    try {
      const r = await fetch("/api/gateway/v1/control/trading", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      const j = await r.json();
      if (!r.ok) {
        setError((j as SignalsResponse).detail ?? `HTTP ${r.status}`);
        return;
      }
      setTradingEnabled(!!(j as { trading_enabled?: boolean }).trading_enabled);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setActionBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070b12] text-zinc-100">
      <header className="border-b border-zinc-800/80 bg-[#070b12]/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-8 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-cyan-400/90">
              RentAI
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
              Trading control center
            </h1>
            <p className="mt-2 max-w-xl text-sm text-zinc-400">
              NSE · NIFTY 50 scope · Optional Groww live LTP when{" "}
              <code className="rounded bg-zinc-800 px-1 text-zinc-300">
                GROWW_AUTH_TOKEN
              </code>{" "}
              + instrument tokens are set on the orchestrator.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => {
                void refresh();
                void refreshBroker();
              }}
              disabled={loading}
              className="rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2 text-sm font-medium text-zinc-100 hover:bg-zinc-800 disabled:opacity-50"
            >
              {loading ? "Refreshing…" : "Refresh signals"}
            </button>
            <button
              type="button"
              onClick={() => void toggleTrading(false)}
              disabled={actionBusy || tradingEnabled === false}
              className="rounded-lg border border-rose-900/80 bg-rose-950/50 px-4 py-2 text-sm font-semibold text-rose-100 hover:bg-rose-900/40 disabled:opacity-40"
            >
              Kill switch
            </button>
            <button
              type="button"
              onClick={() => void toggleTrading(true)}
              disabled={actionBusy || tradingEnabled === true}
              className="rounded-lg border border-emerald-900/80 bg-emerald-950/40 px-4 py-2 text-sm font-semibold text-emerald-100 hover:bg-emerald-900/30 disabled:opacity-40"
            >
              Resume trading
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-10 px-6 py-10">
        <section className="grid gap-6 sm:grid-cols-3">
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-5">
            <p className="text-xs uppercase tracking-wider text-zinc-500">
              Trading state
            </p>
            <p className="mt-2 text-lg font-medium">
              {tradingEnabled === null
                ? "—"
                : tradingEnabled
                  ? "Active"
                  : "Halted"}
            </p>
            <p className="mt-1 text-sm text-zinc-500">
              Orchestrator respects kill switch before any execution path.
            </p>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-5">
            <p className="text-xs uppercase tracking-wider text-zinc-500">
              Signals
            </p>
            <p className="mt-2 text-lg font-medium">{signals.length} symbols</p>
            <p className="mt-1 text-sm text-zinc-500">
              LTP from Groww when configured; decisions are still placeholders until
              your model ships.
            </p>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-5">
            <p className="text-xs uppercase tracking-wider text-zinc-500">
              Groww
            </p>
            <p className="mt-2 text-lg font-medium">
              {broker?.groww_configured ? "Connected" : "Not configured"}
            </p>
            <p className="mt-1 text-sm text-zinc-500">
              {broker?.groww_configured && broker.profile?.ucc
                ? `UCC ${broker.profile.ucc} · ${broker.instruments ?? 0} instruments`
                : "Set GROWW_AUTH_TOKEN + GROWW_INSTRUMENTS_JSON on orchestrator."}
            </p>
            {broker?.groww_allow_place_order ? (
              <p className="mt-2 text-xs font-medium text-rose-400/90">
                API order placement enabled — real orders possible.
              </p>
            ) : null}
          </div>
        </section>

        <p className="text-center text-xs text-zinc-600">
          Stack: Next.js → NestJS gateway → FastAPI orchestrator · Redis optional
        </p>

        {error && (
          <div className="rounded-lg border border-amber-900/60 bg-amber-950/30 px-4 py-3 text-sm text-amber-100">
            <span className="font-semibold">API: </span>
            {error}
            <span className="mt-1 block text-amber-200/80">
              Start Redis, orchestrator (:8000), and gateway (:3001), then set{" "}
              <code className="rounded bg-black/30 px-1">GATEWAY_URL</code> and{" "}
              <code className="rounded bg-black/30 px-1">API_SECRET</code> for
              the Next.js app.
            </span>
          </div>
        )}

        <section>
          <h2 className="text-lg font-semibold tracking-tight">Live signals</h2>
          <p className="mt-1 text-sm text-zinc-500">
            Last traded price (LTP) comes from Groww when tokens are configured.
            Enable{" "}
            <code className="rounded bg-zinc-800 px-1">GROWW_ALLOW_PLACE_ORDER</code>{" "}
            only if you intend to send real orders via the API.
          </p>
          <div className="mt-4 overflow-hidden rounded-xl border border-zinc-800">
            <table className="w-full text-left text-sm">
              <thead className="bg-zinc-900/80 text-xs uppercase text-zinc-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Symbol</th>
                  <th className="px-4 py-3 font-medium">LTP</th>
                  <th className="px-4 py-3 font-medium">Decision</th>
                  <th className="px-4 py-3 font-medium">Confidence</th>
                  <th className="px-4 py-3 font-medium">Note</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/80">
                {signals.length === 0 && !loading && (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-4 py-8 text-center text-zinc-500"
                    >
                      No signals yet.
                    </td>
                  </tr>
                )}
                {signals.map((s) => (
                  <tr key={s.symbol} className="bg-zinc-950/40">
                    <td className="px-4 py-3 font-mono text-zinc-200">
                      {s.symbol}
                    </td>
                    <td className="px-4 py-3 font-mono text-zinc-300">
                      {s.last_price != null && s.last_price !== undefined
                        ? `₹${Number(s.last_price).toFixed(2)}`
                        : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block rounded-md border px-2 py-0.5 text-xs font-semibold ${decisionStyle(s.decision)}`}
                      >
                        {s.decision}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-zinc-300">
                      {(s.confidence * 100).toFixed(0)}%
                    </td>
                    <td className="px-4 py-3 text-zinc-500">{s.rationale}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-xl border border-zinc-800 bg-zinc-950/30 p-6 text-sm text-zinc-400">
          <h3 className="text-base font-semibold text-zinc-200">
            Production checklist
          </h3>
          <ul className="mt-3 list-inside list-disc space-y-2">
            <li>
              Groww: add tokens from the official instrument CSV; rotate any key
              ever pasted into chat.
            </li>
            <li>
              Persist trades and model versions in MongoDB; publish events on
              Redis/Kafka.
            </li>
            <li>
              Add weekly retrain job, risk limits, and alerting (Telegram /
              email).
            </li>
          </ul>
        </section>
      </main>
    </div>
  );
}
