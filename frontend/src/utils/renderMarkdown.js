function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function formatInline(text) {
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  text = text.replace(/(₪[\d,]+(?:\.\d+)?)/g, '<span class="ltr-number">$1</span>')
  return text
}

export function renderMarkdown(text) {
  if (!text) return ''

  const lines = text.split('\n')
  const result = []
  let inTable = false
  let tableRows = []

  function flushTable() {
    if (tableRows.length === 0) return
    let html = '<div class="chat-table-wrap"><table class="chat-table">'
    let headerDone = false
    tableRows.forEach((row) => {
      const cells = row.split('|').filter((_, i, arr) => i > 0 && i < arr.length - 1).map(c => c.trim())
      if (cells.every(c => /^[-:]+$/.test(c))) {
        headerDone = true
        return
      }
      const tag = !headerDone ? 'th' : 'td'
      html += '<tr>' + cells.map(c => `<${tag}>${formatInline(escapeHtml(c))}</${tag}>`).join('') + '</tr>'
    })
    html += '</table></div>'
    result.push(html)
    tableRows = []
    inTable = false
  }

  for (const line of lines) {
    const trimmed = line.trim()
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      inTable = true
      tableRows.push(trimmed)
    } else {
      if (inTable) flushTable()
      if (trimmed) {
        result.push('<p>' + formatInline(escapeHtml(trimmed)) + '</p>')
      }
    }
  }
  if (inTable) flushTable()

  return result.join('')
}
