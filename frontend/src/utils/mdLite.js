// A tiny, SAFE Markdown → HTML renderer for policy documents (headings, lists, tables, bold,
// quotes, rules). Every text node is HTML-escaped first; no links, images or raw HTML pass through.
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, '<code>$1</code>')

export function mdToHtml(md) {
  const out = []
  const lines = String(md || '').split(/\r?\n/)
  let i = 0
  while (i < lines.length) {
    const l = lines[i]
    if (!l.trim()) { i++; continue }
    const h = l.match(/^(#{1,4})\s+(.*)/)
    if (h) { const n = Math.min(h[1].length + 1, 5); out.push(`<h${n}>${inline(h[2])}</h${n}>`); i++; continue }
    if (/^\s*(-{3,}|\*{3,})\s*$/.test(l)) { out.push('<hr>'); i++; continue }
    if (l.trim().startsWith('|')) {
      const rows = []
      while (i < lines.length && lines[i].trim().startsWith('|')) { rows.push(lines[i]); i++ }
      const cells = (r) => r.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim())
      const body = rows.filter((r) => !cells(r).every((c) => /^:?-{2,}:?$/.test(c)))
      if (!body.length) continue
      const [head, ...rest] = body
      out.push('<div class="md-table"><table><thead><tr>' + cells(head).map((c) => `<th>${inline(c)}</th>`).join('') + '</tr></thead><tbody>'
        + rest.map((r) => '<tr>' + cells(r).map((c) => `<td>${inline(c)}</td>`).join('') + '</tr>').join('') + '</tbody></table></div>')
      continue
    }
    if (/^\s*[-*]\s+/.test(l)) {
      const items = []
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) { items.push(lines[i].replace(/^\s*[-*]\s+/, '')); i++ }
      out.push('<ul>' + items.map((t) => `<li>${inline(t)}</li>`).join('') + '</ul>')
      continue
    }
    if (l.startsWith('>')) {
      const q = []
      while (i < lines.length && lines[i].startsWith('>')) { q.push(lines[i].replace(/^>\s?/, '')); i++ }
      out.push(`<blockquote>${inline(q.join(' '))}</blockquote>`)
      continue
    }
    const p = []
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|\s*[-*]\s|\||>)/.test(lines[i])) { p.push(lines[i]); i++ }
    if (!p.length) { out.push(`<p>${inline(l)}</p>`); i++; continue }   // never stall
    out.push(`<p>${inline(p.join(' '))}</p>`)
  }
  return out.join('\n')
}
