import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  isHostProviderId,
  type HostCatalogRow,
  type ProviderOut,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";

const PRESETS: Record<
  string,
  { name: string; base_url: string; auth_style: string; model_name: string }
> = {
  openai: {
    name: "My OpenAI",
    base_url: "https://api.openai.com/v1",
    auth_style: "bearer",
    model_name: "gpt-4o-mini",
  },
  manus: {
    name: "My Manus",
    base_url: "https://api.manus.ai",
    auth_style: "manus",
    model_name: "manus-1.6-lite",
  },
  openrouter: {
    name: "My OpenRouter",
    base_url: "https://openrouter.ai/api/v1",
    auth_style: "bearer",
    model_name: "openai/gpt-4o-mini",
  },
  deepseek: {
    name: "My DeepSeek",
    base_url: "https://api.deepseek.com/v1",
    auth_style: "bearer",
    model_name: "deepseek-v4-flash",
  },
  xai: {
    name: "My xAI",
    base_url: "https://api.x.ai/v1",
    auth_style: "bearer",
    model_name: "grok-4",
  },
  groq: {
    name: "My Groq",
    base_url: "https://api.groq.com/openai/v1",
    auth_style: "bearer",
    model_name: "llama-3.3-70b-versatile",
  },
  merge: {
    name: "My Merge Gateway",
    base_url: "https://api-gateway.merge.dev/v1/openai",
    auth_style: "bearer",
    model_name: "openai/gpt-4o-mini",
  },
  tokenrouter: {
    name: "My TokenRouter",
    base_url: "https://api.tokenrouter.com/v1",
    auth_style: "bearer",
    model_name: "moonshotai/kimi-k3-free",
  },
  modal: {
    name: "My Modal proxy",
    base_url: "https://inference.us-west.modal.direct/v1",
    auth_style: "modal_proxy",
    model_name: "sixscripts--ep-kimi-k3-server.us-west.modal.direct",
  },
  custom: {
    name: "",
    base_url: "https://api.openai.com/v1",
    auth_style: "bearer",
    model_name: "",
  },
};

export default function Providers() {
  const { user, jwt, refreshJwt } = useAuth();
  const [items, setItems] = useState<ProviderOut[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [preset, setPreset] = useState("openai");
  const [name, setName] = useState(PRESETS.openai.name);
  const [baseUrl, setBaseUrl] = useState(PRESETS.openai.base_url);
  const [apiKey, setApiKey] = useState("");
  const [modelName, setModelName] = useState(PRESETS.openai.model_name);
  const [authStyle, setAuthStyle] = useState("bearer");
  const [busy, setBusy] = useState(false);
  const [testing, setTesting] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [catalog, setCatalog] = useState<HostCatalogRow[]>([]);
  const [adminBusy, setAdminBusy] = useState<string | null>(null);

  const host = useMemo(() => items.filter((p) => isHostProviderId(p.id)), [items]);
  const yours = useMemo(() => items.filter((p) => !isHostProviderId(p.id)), [items]);

  async function load() {
    const token = (await refreshJwt()) || jwt;
    if (!token) return;
    try {
      setItems(await api.providers(token));
      const caps = await api.providerCapabilities(token);
      setIsAdmin(!!caps.is_admin);
      if (caps.is_admin) {
        setCatalog(await api.hostCatalog(token));
      } else {
        setCatalog([]);
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed");
    }
  }
  useEffect(() => {
    load();
  }, [jwt]);

  function applyPreset(k: string) {
    setPreset(k);
    const p = PRESETS[k] || PRESETS.custom;
    setName(p.name);
    setBaseUrl(p.base_url);
    setAuthStyle(p.auth_style);
    setModelName(p.model_name);
  }

  async function onTest() {
    const token = (await refreshJwt()) || jwt;
    if (!token) return;
    setTesting(true);
    setErr(null);
    setMsg(null);
    try {
      await api.providerHealth(token, {
        base_url: baseUrl,
        api_key: apiKey,
        auth_style: authStyle,
        model: modelName || undefined,
      });
      setMsg("Key works — 200");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Health failed");
    } finally {
      setTesting(false);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const token = (await refreshJwt()) || jwt;
    if (!token) return;
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      await api.createProvider(token, {
        name,
        base_url: baseUrl,
        api_key: apiKey,
        auth_style: authStyle,
        model_name: modelName,
      });
      setApiKey("");
      setMsg("Saved — shows under Your providers and battle slots");
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function saveHostRow(row: HostCatalogRow) {
    const token = (await refreshJwt()) || jwt;
    if (!token) return;
    setAdminBusy(row.id);
    setErr(null);
    setMsg(null);
    try {
      await api.patchHostCatalog(token, row.id, {
        name: row.name,
        base_url: row.base_url,
        model_name: row.model_name,
        enabled: row.enabled,
      });
      setMsg(`Host updated: ${row.id}`);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Host update failed");
    } finally {
      setAdminBusy(null);
    }
  }

  if (!user)
    return (
      <div className="p-8 text-[13px] text-muted">
        Login required — <Link to="/login" className="link">log in</Link>
      </div>
    );

  return (
    <div className="grid grid-cols-12 gap-6">
      <div className="col-span-12 lg:col-span-7 space-y-6">
        <div>
          <h1 className="text-[22px] font-semibold tracking-[-0.01em]">Keys</h1>
          <p className="mt-1 text-[13px] text-muted">
            Host models are always available (operator-funded). Add your own OpenAI, Manus, or
            other keys below to compete. Keys encrypted at rest (Fernet).
          </p>
          <p className="mt-1 font-mono text-[11px] text-muted">Your user id: {user.$id}</p>
        </div>

        <section className="space-y-3">
          <h2 className="text-[12px] font-semibold text-muted uppercase tracking-wide">
            Your providers
          </h2>
          {yours.map((p) => (
            <div key={p.id} className="card p-4 flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-[13px] font-semibold">{p.name}</div>
                <div className="mt-0.5 truncate font-mono text-[11px] text-muted">
                  {p.model_name} • {p.base_url}
                </div>
                <div className="mt-1 font-mono text-[10px] text-muted">
                  {p.id} • {p.masked_key}
                </div>
              </div>
              <span className="tag shrink-0">{p.auth_style}</span>
            </div>
          ))}
          {!yours.length && (
            <div className="rounded-lg border border-dashed border-border p-6 text-[12px] text-muted">
              No personal keys yet — add OpenAI, Manus, Grok, etc. from the form to compete.
            </div>
          )}
        </section>

        <section className="space-y-3">
          <h2 className="text-[12px] font-semibold text-muted uppercase tracking-wide">
            Host (shared) — always available
          </h2>
          <p className="text-[12px] text-muted">
            Not editable here — shared catalog for every battle. Use Your providers for your own
            keys.
          </p>
          {host.map((p) => (
            <div key={p.id} className="card p-4 flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-[13px] font-semibold">{p.name}</div>
                <div className="mt-0.5 truncate font-mono text-[11px] text-muted">
                  {p.id} • {p.model_name}
                </div>
              </div>
              <span className="tag shrink-0 border-accent/40 text-accent">HOST</span>
            </div>
          ))}
        </section>

        {isAdmin && (
          <section className="space-y-3">
            <h2 className="text-[12px] font-semibold text-muted uppercase tracking-wide">
              Admin — host catalog
            </h2>
            <p className="text-[12px] text-muted">
              Edit display name, base URL, model id, or disable a host entry. Secrets stay in
              server env — not editable in UI.
            </p>
            {catalog.map((row) => (
              <div key={row.id} className="card p-4 space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-mono text-[11px] text-muted">{row.id}</div>
                  <div className="flex items-center gap-2 text-[11px]">
                    <span className={row.configured ? "text-success" : "text-danger"}>
                      {row.configured ? "creds ok" : "creds missing"}
                    </span>
                    <label className="flex items-center gap-1">
                      <input
                        type="checkbox"
                        checked={row.enabled}
                        onChange={(e) =>
                          setCatalog((prev) =>
                            prev.map((r) =>
                              r.id === row.id ? { ...r, enabled: e.target.checked } : r
                            )
                          )
                        }
                      />
                      enabled
                    </label>
                  </div>
                </div>
                <div className="grid grid-cols-1 gap-2">
                  <input
                    className="input"
                    value={row.name}
                    onChange={(e) =>
                      setCatalog((prev) =>
                        prev.map((r) => (r.id === row.id ? { ...r, name: e.target.value } : r))
                      )
                    }
                    placeholder="Display name"
                  />
                  <input
                    className="input font-mono text-[12px]"
                    value={row.base_url}
                    onChange={(e) =>
                      setCatalog((prev) =>
                        prev.map((r) =>
                          r.id === row.id ? { ...r, base_url: e.target.value } : r
                        )
                      )
                    }
                    placeholder="Base URL"
                  />
                  <input
                    className="input font-mono text-[12px]"
                    value={row.model_name}
                    onChange={(e) =>
                      setCatalog((prev) =>
                        prev.map((r) =>
                          r.id === row.id ? { ...r, model_name: e.target.value } : r
                        )
                      )
                    }
                    placeholder="Model name"
                  />
                </div>
                <button
                  type="button"
                  className="btn btn-ghost h-9 text-[12px]"
                  disabled={adminBusy === row.id}
                  onClick={() => saveHostRow(row)}
                >
                  {adminBusy === row.id ? "Saving…" : "Save host"}
                </button>
              </div>
            ))}
          </section>
        )}
      </div>

      <div className="col-span-12 lg:col-span-5">
        <div className="card p-6 h-fit sticky top-[72px]">
          <h3 className="text-[15px] font-semibold tracking-[-0.01em] mb-4">Add / update key</h3>
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium">Preset</label>
              <select className="select" value={preset} onChange={(e) => applyPreset(e.target.value)}>
                {Object.keys(PRESETS).map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium">Name</label>
              <input className="input" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium">Base URL</label>
              <input
                className="input"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium">API key</label>
              <input
                className="input"
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium">Model name</label>
              <input
                className="input"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium">Auth style</label>
              <select
                className="select"
                value={authStyle}
                onChange={(e) => setAuthStyle(e.target.value)}
              >
                <option value="bearer">bearer</option>
                <option value="manus">manus</option>
                <option value="modal_proxy">modal_proxy</option>
              </select>
            </div>
            {msg && (
              <div className="rounded-md border border-success bg-success/10 px-3 py-2 text-[12px] text-success">
                {msg}
              </div>
            )}
            {err && (
              <div className="rounded-md border border-danger bg-danger/10 px-3 py-2 text-[12px] text-danger break-all">
                {err}
              </div>
            )}
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                disabled={testing || !apiKey}
                onClick={onTest}
                className="btn btn-ghost h-10 text-[12px]"
              >
                {testing ? "Testing…" : "Test key"}
              </button>
              <button disabled={busy} className="btn btn-primary h-10 text-[12px]">
                {busy ? "Saving…" : "Save →"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
