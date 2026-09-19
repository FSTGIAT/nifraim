/**
 * Hebrew wording for what an agreement extraction actually did.
 *
 * A PDF that yields no rates used to be completely silent: `chat.js` only
 * spoke when `rates.length` was truthy, so the upload reported success, the
 * agreement shelf did not move, and no reason was given. Measured on the real
 * ילין לפידות agreement, whose §4.1 defers every rate to a נספח א' that was
 * never scanned — "0 rates" was the CORRECT answer, delivered as silence.
 *
 * The backend now returns `structured_data.extraction`
 * ({proposed, kept, dropped[], verified, text_source, appendix_ref,
 * zero_reason}); this turns it into something an agent can act on.
 */

const DROP_REASONS = {
  non_commission_filter: 'עמלת היקף / החזר — לא עמלת נפרעים',
  non_commission_scope: 'רכיב של עמלת היקף / החזר',
  value_not_in_text: 'הערך לא נמצא בטקסט המסמך',
  no_usable_component: 'ללא שיעור קריא',
}

const ZERO_REASONS = {
  appendix_missing:
    'ההסכם מפנה לנספח התמורה, והנספח אינו כלול בקובץ — העלה גם אותו כדי לחלץ שיעורים.',
  all_rows_dropped:
    'נמצאו שורות שיעורים אך כולן נפסלו — ראה פירוט למטה.',
  rate_table_present_but_unparsed:
    'נראה שיש טבלת שיעורים במסמך, אך לא זוהו ממנה שורות של עמלת נפרעים.',
  no_readable_text:
    'לא ניתן היה לקרוא טקסט מהקובץ (סריקה ללא שכבת טקסט, וגם ה-OCR לא החזיר טקסט).',
  no_rates_in_document:
    'לא נמצאה במסמך טבלה של שיעורי עמלת נפרעים.',
}

export function dropReasonLabel(reason) {
  return DROP_REASONS[reason] || reason || 'נפסל'
}

/** `{ text, tone }` — the one line to show after an agreement upload. */
export function extractionOutcome(extraction, rates = []) {
  const kept = extraction?.kept ?? rates.length
  if (kept > 0) {
    const line = `חולצו **${kept}** שיעורי עמלה — נוספו לטבלת השיעורים.`
    // A scanned agreement with no readable text cannot be checked against the
    // document's own words, so nothing here was verified.
    if (extraction && extraction.verified === false) {
      return {
        tone: 'warn',
        text: `${line}\n\nשים לב: לא הייתה שכבת טקסט לאימות, כך שהשיעורים לא הושוו מול נוסח המסמך. מומלץ לעבור עליהם.`,
      }
    }
    return { tone: 'ok', text: line }
  }

  const why = ZERO_REASONS[extraction?.zero_reason] || ZERO_REASONS.no_rates_in_document
  let text = `**לא נוספו שיעורי עמלה.** ${why}`
  const dropped = extraction?.dropped || []
  if (dropped.length) {
    const counts = new Map()
    for (const d of dropped) {
      counts.set(d.reason, (counts.get(d.reason) || 0) + 1)
    }
    const parts = [...counts.entries()].map(([r, n]) => `${dropReasonLabel(r)} (${n})`)
    text += `\n\nנפסלו ${dropped.length} שורות: ${parts.join(' · ')}`
  }
  return { tone: 'warn', text }
}
