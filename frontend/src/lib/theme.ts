const DARK_CLASS = "dark";

function prefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function applySystemTheme(): void {
  document.documentElement.classList.toggle(DARK_CLASS, prefersDark());
}

export function subscribeSystemTheme(): () => void {
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  const onChange = () => applySystemTheme();
  mq.addEventListener("change", onChange);
  return () => mq.removeEventListener("change", onChange);
}
