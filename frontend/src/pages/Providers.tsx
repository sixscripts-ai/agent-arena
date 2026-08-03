import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, isHostProviderId, type ProviderOut } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const PRESETS: Record<string, { name: string; base_url: string; auth_style: string; model_name: string }> = {
  openai: { name: "My OpenAI", base_url: "https://api.openai.com/v1", auth_style: "bearer", model_name: "gpt-4o-mini" },
  openrouter: { name: "My OpenRouter", base_url: "https://openrouter.ai/api/v1", auth_style: "bearer", model_name: "openai/gpt-4o-mini" },
  deepseek: { name: "My DeepSeek", base_url: "https://api.deepseek.com/v1", auth_style: "bearer", model_name: "deepseek-chat" },
  xai: { name: "My xAI", base_url: "https://api.x.ai/v1", auth_style: "bearer", model_name: "grok-4" },
  groq: { name: "My Groq", base_url: "https://api.groq.com/openai/v1", auth_style: "bearer", model_name: "llama-3.3-70b-versatile" },
  meta: { name: "My Meta", base_url: "https://api.llama.com/v1", auth_style: "bearer", model_name: "Llama-4-Maverick-17B-128E-Instruct" },
  mistral: { name: "My Mistral", base_url: "https://api.mistral.ai/v1", auth_style: "bearer", model_name: "mistral-large-latest" },
  custom: { name: "", base_url: "https://api.openai.com/v1", auth_style: "bearer", model_name: "" },
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

  if (!user) return <div className="p-8 mono text-[12px]">Login required — <Link to="/login" className="underline">LOG IN</Link></div>;

  return (
    <div className="grid grid-cols-12 gap-6">
      <div className="col-span-12 lg:col-span-7 space-y-6">
        <div className="border-b-[1.5px] border-ink pb-4">
          <h1 className="display text-[32px]">KEYS // BYOK + HOST</h1>
          <p className="mono text-[11px] text-zinc-500 mt-1">Host free always — DeepSeek, OpenRouter, Groq. Add yours to compete. Keys encrypted at rest (Fernet).</p>
        </div>
        <section className="space-y-3">
          <h2 className="mono text-[11px] uppercase tracking-widest bg-ink text-paper inline-block px-2 py-1">Your providers</h2>
          {yours.map(p=>(
            <div key={p.id} className="border-[1.5px] border-ink p-4 bg-paper flex justify-between">
              <div>
                <div className="font-bold text-[13px]">{p.name}</div>
                <div className="mono text-[11px] text-zinc-600">{p.id} • {p.model_name} • {p.base_url}</div>
                <div className="mono text-[10px] text-zinc-500">{p.masked_key}</div>
              </div>
              <span className="h-fit border border-ink px-2 py-0.5 mono text-[10px]">{p.auth_style}</span>
            </div>
          ))}
          {!yours.length && <div className="border-[1.5px] border-dashed border-ink p-6 mono text-[12px]">No personal keys — use form → add OpenAI, DeepSeek, Grok, etc.</div>}
        </section>
        <section className="space-y-3">
          <h2 className="mono text-[11px] uppercase tracking-widest bg-blueprint text-white inline-block px-2 py-1">Host (read-only)</h2>
          {host.map(p=>(
            <div key={p.id} className="border-[1.5px] border-blueprint bg-blueprint/5 p-4 flex justify-between">
              <div>
                <div className="font-bold text-[13px]">{p.name}</div>
                <div className="mono text-[11px] text-zinc-600">{p.id} • {p.model_name}</div>
              </div>
              <span className="h-fit bg-blueprint text-white px-2 py-0.5 mono text-[10px]">HOST</span>
            </div>
          ))}
        </section>
      </div>
      <div className="col-span-12 lg:col-span-5 border-[1.5px] border-ink bg-paper p-6 h-fit sticky top-[72px]">
        <h3 className="display text-[18px] mb-4">Add / Update Key</h3>
        <form onSubmit={onSubmit} className="space-y-3">
          <div><label className="mono text-[10px] uppercase">Preset</label><select className="w-full h-10 border-[1.5px] border-ink px-3 text-[13px] bg-paper" value={preset} onChange={e=>applyPreset(e.target.value)}>{Object.keys(PRESETS).map(k=><option key={k} value={k}>{k}</option>)}</select></div>
          <div><label className="mono text-[10px] uppercase">Name</label><input className="w-full h-10 border-[1.5px] border-ink px-3 text-[13px]" value={name} onChange={e=>setName(e.target.value)} required /></div>
          <div><label className="mono text-[10px] uppercase">Base URL</label><input className="w-full h-10 border-[1.5px] border-ink px-3 text-[13px]" value={baseUrl} onChange={e=>setBaseUrl(e.target.value)} required /></div>
          <div><label className="mono text-[10px] uppercase">API Key</label><input className="w-full h-10 border-[1.5px] border-ink px-3 text-[13px]" type="password" value={apiKey} onChange={e=>setApiKey(e.target.value)} required /></div>
          <div><label className="mono text-[10px] uppercase">Model Name</label><input className="w-full h-10 border-[1.5px] border-ink px-3 text-[13px]" value={modelName} onChange={e=>setModelName(e.target.value)} required /></div>
          <div><label className="mono text-[10px] uppercase">Auth Style</label><select className="w-full h-10 border-[1.5px] border-ink px-3 text-[13px] bg-paper" value={authStyle} onChange={e=>setAuthStyle(e.target.value)}><option value="bearer">bearer</option><option value="modal_proxy">modal_proxy</option></select></div>
          {msg && <div className="border border-success bg-success/10 px-3 py-2 mono text-[11px] text-success">{msg}</div>}
          {err && <div className="border border-vermillion bg-vermillion/10 px-3 py-2 mono text-[11px] text-vermillion break-all">{err}</div>}
          <div className="grid grid-cols-2 gap-2">
            <button type="button" disabled={testing || !apiKey} onClick={onTest} className="h-10 border-[1.5px] border-ink bg-paper mono text-[11px] font-bold hover:bg-ink hover:text-paper disabled:opacity-50">{testing ? "TESTING..." : "TEST KEY"}</button>
            <button disabled={busy} className="h-10 bg-ink text-paper mono text-[11px] font-bold border-[1.5px] border-ink hover:bg-paper hover:text-ink">{busy ? "SAVING..." : "SAVE →"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
