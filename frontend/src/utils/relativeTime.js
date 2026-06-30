// Hebrew relative time — "לפני 5 דק׳", "לפני 3 שעות", "אתמול", "לפני 4 ימים"
// Falls back to absolute date for anything older than a week.
export function relativeHebrew(input) {
  if (!input) return ''
  let d
  if (input instanceof Date) {
    d = input
  } else {
    // The backend sends naive UTC timestamps (datetime.utcnow().isoformat()) with
    // NO timezone designator. JS parses a tz-less datetime as LOCAL time, so in
    // Israel (UTC+2/+3) a worker seen moments ago reads "לפני 3 שעות". Treat a
    // tz-less datetime string as UTC by appending 'Z' before parsing.
    let s = String(input)
    if (/T\d{2}:\d{2}/.test(s) && !/([zZ]|[+-]\d{2}:?\d{2})$/.test(s)) s += 'Z'
    d = new Date(s)
  }
  if (isNaN(d.getTime())) return ''
  const diffMs = Date.now() - d.getTime()
  if (diffMs < 0) return 'הרגע'
  const sec = Math.floor(diffMs / 1000)
  if (sec < 30) return 'הרגע'
  if (sec < 60) return `לפני ${sec} שנ׳`
  const min = Math.floor(sec / 60)
  if (min < 60) return `לפני ${min} דק׳`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `לפני ${hr === 1 ? 'שעה' : hr + ' שעות'}`
  const day = Math.floor(hr / 24)
  if (day === 1) return 'אתמול'
  if (day < 7) return `לפני ${day} ימים`
  // Older: absolute date
  return d.toLocaleDateString('he-IL', { day: '2-digit', month: '2-digit', year: '2-digit' })
}
