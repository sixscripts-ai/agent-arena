"use client";

import { useEffect, useState } from "react";
import { api, type FormatOut, type LeaderboardRow } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function LeaderboardPage() {
  const { jwt } = useAuth();
  const [rows, setRows] = useState<LeaderboardRow[]>([]);
  const [formats, setFormats] = useState<FormatOut[]>([]);
  const [formatId, setFormatId] = useState("overall");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        if (jwt) setFormats(await api.formats(jwt));
      } catch {
        /* optional */
      }
    })();
  }, [jwt]);

  useEffect(() => {
    (async () => {
      try {
        const data = await api.leaderboard(jwt, formatId || "overall");
        setRows(Array.isArray(data) ? data : []);
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed");
        setRows([]);
      }
    })();
  }, [jwt, formatId]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Leaderboard</h1>
      <div className="flex flex-wrap gap-3">
        <select
          className="h-10 rounded-md border border-zinc-700 bg-zinc-900 px-3 text-sm"
          value={formatId}
          onChange={(e) => setFormatId(e.target.value)}
        >
          <option value="overall">Overall</option>
          {formats.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
            </option>
          ))}
        </select>
      </div>
      {error && <p className="text-sm text-amber-400">{error}</p>}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Elo rankings</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-zinc-500">
                <tr>
                  <th className="pb-2 pr-4">#</th>
                  <th className="pb-2 pr-4">Model</th>
                  <th className="pb-2 pr-4">Format</th>
                  <th className="pb-2 pr-4">Elo</th>
                  <th className="pb-2">Games</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={`${r.model_id}-${r.format_id}-${i}`} className="border-t border-zinc-800">
                    <td className="py-2 pr-4 text-zinc-500">{i + 1}</td>
                    <td className="py-2 pr-4 font-mono text-xs">{r.model_id}</td>
                    <td className="py-2 pr-4 text-zinc-400">{r.format_id}</td>
                    <td className="py-2 pr-4 text-emerald-400">{Math.round(r.elo)}</td>
                    <td className="py-2">{r.games_played}</td>
                  </tr>
                ))}
                {!rows.length && (
                  <tr>
                    <td colSpan={5} className="py-6 text-zinc-500">
                      No rankings yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
