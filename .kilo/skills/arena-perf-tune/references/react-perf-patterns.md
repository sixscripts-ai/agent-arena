# React Perf Patterns for Arena

## Problem: LiveBattle arts.filter each render

Current:
```ts
const codeA = useMemo(()=> arts.filter(a=>a.model_id===modelA)...
```
Better:
```ts
const modelMap = useRef<Map<string, string[]>>(new Map())
useEffect(()=>{
  for last art only, append to map
}, [arts])
```

## Scroll thrash

Bad: `useEffect(()=> bottomRef.current?.scrollIntoView({behavior:"smooth"}) , [arts])` triggers layout every token.
Good: rAF debounce, check if user at bottom (auto-scroll only if already near bottom).

```ts
const raf = useRef(0)
useEffect(()=>{
  if (raf.current) cancelAnimationFrame(raf.current)
  raf.current = requestAnimationFrame(()=> bottomRef.current?.scrollIntoView({behavior:"instant"}))
},[arts])
```

## setInterval leak in auth

Current init creates interval forever, never cleared, called per SiteHeader mount.
Fix: in useAuth, store interval id, clear on logout, useEffect cleanup in component that calls init.

## CodePane split

`code.split("\n")` on every render heavy for 50kb. Memoize.

```ts
const lines = useMemo(()=> code.split("\n"), [code])
```

Or virtualize with react-window for >200 lines.

## Bundle

- lucide-react individual imports: `import { Trophy } from "lucide-react"` tree-shaken but better `import Trophy from "lucide-react/dist/esm/icons/trophy"`? Check Vite analyzer.
- Dynamic import DesignOptions (contains many designs) + DesignMockup.

## SWR for formats

Formats change slowly. Use stale-while-revalidate 60s to avoid Home refetch flash 0.

```ts
const {data} = useSWR('/formats', fetcher, {dedupingInterval:60000})
```

## SSE

Current reader splits "\n" but SSE spec lines: event:, data:, id:, retry:. Only handles event/data. Add id handling for Last-Event-ID resume.
