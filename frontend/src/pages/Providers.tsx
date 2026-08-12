import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api, isHostProviderId, type ProviderOut } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { authRoute, currentInternalReturn } from "@/lib/authReturn";

const PRESETS: Record<string, { name: string; base_url: string; auth_style: string; model_name: string }> = {
  openai: { name: "My OpenAI", base_url: "https://api.openai.com/v1", auth_style: "bearer", model_name: "gpt-4o-mini" },
  openrouter: { name: "My OpenRouter", base_url: "https://openrouter.ai/api/v1", auth_style: "bearer", model_name: "openai/gpt-4o-mini" },
  deepseek: { name: "My DeepSeek", base_url: "https://api.deepseek.com/v1", auth_style: "bearer", model_name: "deepseek-v4-flash" },
  xai: { name: "My xAI", base_url: "https://api.x.ai/v1", auth_style: "bearer", model_name: "grok-4" },
  groq: { name: "My Groq", base_url: "https://api.groq.com/openai/v1", auth_style: "bearer", model_name: "llama-3.3-70b-versatile" },
  meta: { name: "My Meta", base_url: "https://api.meta.ai/v1", auth_style: "bearer", model_name: "muse-spark-1.1" },
  mistral: { name: "My Mistral", base_url: "https://api.mistral.ai/v1", auth_style: "bearer", model_name: "mistral-large-latest" },
  custom: { name: "", base_url: "https://api.openai.com/v1", auth_style: "bearer", model_name: "" },
};

export default function Providers() {
  const { user, jwt, refreshJwt } = useAuth();
  const loc = useLocation();
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

  const host = useMemo(()=>items.filter(p=>isHostProviderId(p.id)), [items]);
  const yours = useMemo(()=>items.filter(p=>!isHostProviderId(p.id)), [items]);

  async function load() {
    const token = (await refreshJwt()) || jwt;
    if (!token) return;
    try { setItems(await api.providers(token)); } catch (e) { setErr(e instanceof Error ? e.message : "Failed"); }
  }
  useEffect(()=>{ load(); }, [jwt]);

  function applyPreset(k: string) {
    setPreset(k);
    const p = PRESETS[k] || PRESETS.custom;
    setName(p.name); setBaseUrl(p.base_url); setAuthStyle(p.auth_style); setModelName(p.model_name);
  }

  async function onTest() {
    const token = (await refreshJwt()) || jwt;
    if (!token) return;
    setTesting(true); setErr(null); setMsg(null);
    try { await api.providerHealth(token, { base_url: baseUrl, api_key: apiKey, auth_style: authStyle, model: modelName || undefined }); setMsg("Key works — 200"); } catch (e) { setErr(e instanceof Error ? e.message : "Health failed"); } finally { setTesting(false); }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const token = (await refreshJwt()) || jwt;
    if (!token) return;
    setBusy(true); setErr(null); setMsg(null);
    try {
      await api.createProvider(token, { name, base_url: baseUrl, api_key: apiKey, auth_style: authStyle, model_name: modelName });
      setApiKey(""); setMsg("Saved — shows under Your providers and battle slots");
      await load();
    } catch (e) { setErr(e instanceof Error ? e.message : "Save failed"); } finally { setBusy(false); }
  }

  if (!user) return <div className="p-8 text-[13px] text-muted">Login required — <Link to={authRoute("login", currentInternalReturn(loc))} className="link">log in</Link></div>;

  return (
    <div className="grid grid-cols-12 gap-6">
      <div className="col-span-12 lg:col-span-7 space-y-6">
        <div>
          <h1 className="text-[22px] font-semibold tracking-[-0.01em]">Keys</h1>
          <p className="mt-1 text-[13px] text-muted">Host models are free always — DeepSeek, OpenRouter, Groq. Add your own keys to compete. Keys encrypted at rest (Fernet).</p>
        </div>

        <section className="space-y-3">
          <h2 className="text-[12px] font-semibold text-muted uppercase tracking-wide">Your providers</h2>
          {yours.map(p=>(
            <div key={p.id} className="card p-4 flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-[13px] font-semibold">{p.name}</div>
                <div className="mt-0.5 truncate font-mono text-[11px] text-muted">{p.model_name} • {p.base_url}</div>
                <div className="mt-1 font-mono text-[10px] text-muted">{p.id} • {p.masked_key}</div>
              </div>
              <span className="tag shrink-0">{p.auth_style}</span>
            </div>
          ))}
          {!yours.length && (
            <div className="rounded-lg border border-dashed border-border p-6 text-[12px] text-muted">
              No personal keys yet — add OpenAI, DeepSeek, Grok, etc. from the form to compete.
            </div>
          )}
        </section>

        <section className="space-y-3">
          <h2 className="text-[12px] font-semibold text-muted uppercase tracking-wide">Host — read only</h2>
          {host.map(p=>(
            <div key={p.id} className="card p-4 flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-[13px] font-semibold">{p.name}</div>
                <div className="mt-0.5 truncate font-mono text-[11px] text-muted">{p.id} • {p.model_name}</div>
              </div>
              <span className="tag shrink-0 border-accent/40 text-accent">HOST</span>
            </div>
          ))}
        </section>
      </div>

      <div className="col-span-12 lg:col-span-5">
        <div className="card p-6 h-fit sticky top-[72px]">
          <h3 className="text-[15px] font-semibold tracking-[-0.01em] mb-4">Add / update key</h3>
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium">Preset</label>
              <select className="select" value={preset} onChange={e=>applyPreset(e.target.value)}>
                {Object.keys(PRESETS).map(k=><option key={k} value={k}>{k}</option>)}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium">Name</label>
              <input className="input" value={name} onChange={e=>setName(e.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium">Base URL</label>
              <input className="input" value={baseUrl} onChange={e=>setBaseUrl(e.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium">API key</label>
              <input className="input" type="password" value={apiKey} onChange={e=>setApiKey(e.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium">Model name</label>
              <input className="input" value={modelName} onChange={e=>setModelName(e.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium">Auth style</label>
              <select className="select" value={authStyle} onChange={e=>setAuthStyle(e.target.value)}>
                <option value="bearer">bearer</option>
                <option value="modal_proxy">modal_proxy</option>
              </select>
            </div>
            {msg && <div className="rounded-md border border-success bg-success/10 px-3 py-2 text-[12px] text-success">{msg}</div>}
            {err && <div className="rounded-md border border-danger bg-danger/10 px-3 py-2 text-[12px] text-danger break-all">{err}</div>}
            <div className="grid grid-cols-2 gap-2">
              <button type="button" disabled={testing || !apiKey} onClick={onTest} className="btn btn-ghost h-10 text-[12px]">
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
