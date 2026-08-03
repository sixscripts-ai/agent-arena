"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, isHostProviderId, type ProviderOut } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

const PRESETS: Record<
  string,
  { name: string; base_url: string; auth_style: string; model_name: string }
> = {
  custom: {
    name: "",
    base_url: "https://api.openai.com/v1",
    auth_style: "bearer",
    model_name: "",
  },
  openai: {
    name: "My OpenAI",
    base_url: "https://api.openai.com/v1",
    auth_style: "bearer",
    model_name: "gpt-4o-mini",
  },
  openrouter: {
    name: "My OpenRouter",
    base_url: "https://openrouter.ai/api/v1",
    auth_style: "bearer",
    model_name: "openai/gpt-4o-mini",
  },
  xai: {
    name: "My xAI",
    base_url: "https://api.x.ai/v1",
    auth_style: "bearer",
    model_name: "grok-4-1-fast-non-reasoning",
  },
  deepseek: {
    name: "My DeepSeek",
    base_url: "https://api.deepseek.com/v1",
    auth_style: "bearer",
    model_name: "deepseek-chat",
  },
};

function ProviderCard({ p, host }: { p: ProviderOut; host?: boolean }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">{p.name}</CardTitle>
          <div className="flex gap-1">
            {host && <Badge>host</Badge>}
            <Badge>{p.auth_style}</Badge>
          </div>
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
  );
}

export default function ProvidersPage() {
  const { user, jwt, loading } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<ProviderOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [healthMsg, setHealthMsg] = useState<string | null>(null);
  const [preset, setPreset] = useState("openai");
  const [name, setName] = useState(PRESETS.openai.name);
  const [baseUrl, setBaseUrl] = useState(PRESETS.openai.base_url);
  const [apiKey, setApiKey] = useState("");
  const [modelName, setModelName] = useState(PRESETS.openai.model_name);
  const [authStyle, setAuthStyle] = useState(PRESETS.openai.auth_style);
  const [busy, setBusy] = useState(false);
  const [testing, setTesting] = useState(false);

  const hostItems = useMemo(() => items.filter((p) => isHostProviderId(p.id)), [items]);
  const userItems = useMemo(() => items.filter((p) => !isHostProviderId(p.id)), [items]);

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

  function applyPreset(key: string) {
    setPreset(key);
    const p = PRESETS[key] || PRESETS.custom;
    setName(p.name);
    setBaseUrl(p.base_url);
    setAuthStyle(p.auth_style);
    setModelName(p.model_name);
  }

  async function onTest() {
    if (!jwt || !apiKey || !baseUrl) return;
    setTesting(true);
    setHealthMsg(null);
    setError(null);
    try {
      await api.providerHealth(jwt, {
        base_url: baseUrl,
        api_key: apiKey,
        auth_style: authStyle,
        model: modelName || undefined,
      });
      setHealthMsg("Key works — chat completions returned 200.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Health check failed");
    } finally {
      setTesting(false);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!jwt) return;
    setBusy(true);
    setError(null);
    setHealthMsg(null);
    try {
      await api.createProvider(jwt, {
        name,
        base_url: baseUrl,
        api_key: apiKey,
        auth_style: authStyle,
        model_name: modelName,
      });
      setApiKey("");
      setHealthMsg("Saved. It will show under Your providers and in battle slots.");
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
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">Providers</h1>
          <p className="mt-1 text-sm text-zinc-400">
            Add your own API keys to compete with host models. Keys are encrypted at rest.
            After saving, pick them on{" "}
            <Link href="/battles/new" className="text-emerald-400 hover:underline">
              New Battle
            </Link>
            .
          </p>
        </div>

        <section className="space-y-3">
          <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500">
            Your providers
          </h2>
          {userItems.map((p) => (
            <ProviderCard key={p.id} p={p} />
          ))}
          {!userItems.length && (
            <p className="text-sm text-zinc-500">
              No personal keys yet — use the form to add OpenAI, xAI, DeepSeek, or any
              OpenAI-compatible endpoint.
            </p>
          )}
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500">
            Host (read-only)
          </h2>
          {hostItems.map((p) => (
            <ProviderCard key={p.id} p={p} host />
          ))}
        </section>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Add / update your key</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-3">
            <div className="space-y-1">
              <Label>Preset</Label>
              <select
                className="flex h-10 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 text-sm"
                value={preset}
                onChange={(e) => applyPreset(e.target.value)}
              >
                <option value="openai">OpenAI</option>
                <option value="openrouter">OpenRouter</option>
                <option value="xai">xAI (Grok)</option>
                <option value="deepseek">DeepSeek</option>
                <option value="custom">Custom</option>
              </select>
            </div>
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
                placeholder="e.g. gpt-4o-mini"
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
            {healthMsg && <p className="text-sm text-emerald-400">{healthMsg}</p>}
            {error && <p className="text-sm text-red-400 break-all">{error}</p>}
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                className="flex-1"
                disabled={testing || !apiKey}
                onClick={onTest}
              >
                {testing ? "Testing…" : "Test key"}
              </Button>
              <Button type="submit" disabled={busy} className="flex-1">
                {busy ? "Saving…" : "Save provider"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
