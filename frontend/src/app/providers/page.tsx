"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type ProviderOut } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

export default function ProvidersPage() {
  const { user, jwt, loading } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<ProviderOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://openrouter.ai/api/v1");
  const [apiKey, setApiKey] = useState("");
  const [modelName, setModelName] = useState("");
  const [authStyle, setAuthStyle] = useState("bearer");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  async function load() {
    if (!jwt) return;
    try {
      setItems(await api.providers(jwt));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jwt]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!jwt) return;
    setBusy(true);
    setError(null);
    try {
      await api.createProvider(jwt, {
        name,
        base_url: baseUrl,
        api_key: apiKey,
        auth_style: authStyle,
        model_name: modelName,
      });
      setName("");
      setApiKey("");
      setModelName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  if (loading || !user) return <p className="text-zinc-500">Loading…</p>;

  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Providers</h1>
        <p className="text-sm text-zinc-400">
          Keys stay encrypted on the backend. Host free model is always available.
        </p>
        <div className="space-y-3">
          {items.map((p) => (
            <Card key={p.id}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between gap-2">
                  <CardTitle className="text-base">{p.name}</CardTitle>
                  <Badge>{p.auth_style}</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-1 text-sm text-zinc-400">
                <div>
                  <span className="text-zinc-500">id:</span> {p.id}
                </div>
                <div>
                  <span className="text-zinc-500">model:</span> {p.model_name}
                </div>
                <div>
                  <span className="text-zinc-500">url:</span> {p.base_url}
                </div>
                <div>
                  <span className="text-zinc-500">key:</span> {p.masked_key}
                </div>
              </CardContent>
            </Card>
          ))}
          {!items.length && (
            <p className="text-sm text-zinc-500">No providers yet.</p>
          )}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Add / update provider</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-3">
            <div className="space-y-1">
              <Label>Name</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="space-y-1">
              <Label>Base URL</Label>
              <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} required />
            </div>
            <div className="space-y-1">
              <Label>API key</Label>
              <Input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <Label>Model name</Label>
              <Input
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                placeholder="e.g. grok-3"
                required
              />
            </div>
            <div className="space-y-1">
              <Label>Auth style</Label>
              <select
                className="flex h-10 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 text-sm"
                value={authStyle}
                onChange={(e) => setAuthStyle(e.target.value)}
              >
                <option value="bearer">bearer</option>
                <option value="modal_proxy">modal_proxy</option>
                <option value="custom">custom</option>
              </select>
            </div>
            {error && <p className="text-sm text-red-400">{error}</p>}
            <Button type="submit" disabled={busy} className="w-full">
              {busy ? "Saving…" : "Save provider"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
