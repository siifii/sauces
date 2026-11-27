// Minimal, dependency-free i18n for static sites.
// - Elements with data-i18n="key" get their text from locales/<lang>.json.
//   data-i18n-args='{"name": "Alex"}' fills {name}; data-i18n-count="2" picks key.one /
//   key.other (any Intl.PluralRules category) and fills {count}.
// - data-i18n-attr="aria-label:key;placeholder:key2" fills attributes.
// - Sets <html lang dir>. The source-locale text stays in the HTML as the no-JS fallback.

const RTL = ["ar", "he", "fa", "ur"];
const SOURCE = "en";

function format(message, args) {
  return message.replace(/\{(\w+)\}/g, (match, name) => (name in args ? String(args[name]) : match));
}

function lookup(messages, key, args, plural) {
  if (args.count === undefined) return messages[key];
  return messages[`${key}.${plural.select(args.count)}`] ?? messages[`${key}.other`];
}

export function initialLocale() {
  const fromQuery = new URLSearchParams(location.search).get("lang");
  return (fromQuery || navigator.language || SOURCE).split("-")[0].toLowerCase();
}

export async function setLocale(lang) {
  const response = await fetch(new URL(`locales/${lang}.json`, import.meta.url));
  if (!response.ok) {
    if (lang !== SOURCE) return setLocale(SOURCE);
    throw new Error(`missing locales/${SOURCE}.json`);
  }
  const messages = await response.json();
  const plural = new Intl.PluralRules(lang);
  document.documentElement.lang = lang;
  document.documentElement.dir = RTL.includes(lang) ? "rtl" : "ltr";

  for (const el of document.querySelectorAll("[data-i18n]")) {
    const args = JSON.parse(el.dataset.i18nArgs || "{}");
    if (el.dataset.i18nCount !== undefined) args.count = Number(el.dataset.i18nCount);
    const message = lookup(messages, el.dataset.i18n, args, plural);
    if (message !== undefined) el.textContent = format(message, args);
  }
  for (const el of document.querySelectorAll("[data-i18n-attr]")) {
    for (const pair of el.dataset.i18nAttr.split(";")) {
      const [attr, key] = pair.split(":").map((part) => part.trim());
      if (attr && key && messages[key] !== undefined) el.setAttribute(attr, messages[key]);
    }
  }
}
