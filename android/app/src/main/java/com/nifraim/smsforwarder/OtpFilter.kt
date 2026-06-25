package com.nifraim.smsforwarder

import org.json.JSONArray

/**
 * Decides whether an incoming SMS should be forwarded to the server.
 *
 * PRIVACY: the app must NOT forward the user's personal messages. The decision is
 * driven by per-company templates fetched from the backend (so new companies
 * don't need an app update). Logic, in order:
 *
 *   1. a BLOCK template matches             -> DROP   (privacy lever: personal 2FA)
 *   2. an ALLOW template matches            -> FORWARD (a known company OTP)
 *   3. fail-open: body has a 4-8 digit code -> FORWARD (never silently drop a
 *      new/unlisted company's OTP)
 *   4. else                                 -> DROP
 *
 * When NO templates are cached yet (first launch / fetch failed) we fall back to
 * the built-in keyword heuristic below — stricter than fail-open — so the app
 * stays conservative until the real templates arrive, and never regresses to
 * "forward nothing."
 */
object OtpFilter {

    private val CODE_REGEX = Regex("""\d{4,8}""")

    // ---- Built-in fallback heuristic (used only when no templates cached) ----

    // Distinctive company names + English sender IDs. Deliberately EXCLUDES bare
    // common Hebrew words like "כלל" / "מור" (they appear in everyday text).
    private val COMPANY_KEYWORDS = listOf(
        "מגדל", "הפניקס", "פניקס", "הראל", "מנורה", "אלטשולר", "הכשרה",
        "אקסלנס", "איילון", "מבטחים", "מיטב", "אינפיניטי", "אנליסט", "ילין",
        "migdal", "phoenix", "fnx", "harel", "clal", "menora", "altshuler",
        "hachshara", "excellence", "ayalon", "meitav", "infinity", "analyst",
        "mivtachim", "yelin", "more-invest", "morefund",
    )

    private val OTP_PHRASES = listOf(
        "קוד", "אימות", "סיסמ", "חד פעמי", "חד-פעמי", "להזדהות", "כניסה למערכת",
        "otp", "verification", "one-time", "one time", "passcode", "login code",
    )

    /** A compiled template fetched from the backend. */
    data class Template(val pattern: Regex, val isBlock: Boolean)

    /**
     * Parse the cached templates JSON (the backend's `templates` array:
     * `[{"company_name","pattern","is_block"}, ...]`). Patterns are compiled
     * case-insensitive + dot-matches-newline so multi-line SMS match and the
     * stored regex stays portable (no inline flags). Invalid regexes are skipped.
     */
    fun parseTemplates(json: String?): List<Template> {
        if (json.isNullOrBlank()) return emptyList()
        val out = ArrayList<Template>()
        try {
            val arr = JSONArray(json)
            for (i in 0 until arr.length()) {
                val o = arr.optJSONObject(i) ?: continue
                val pat = o.optString("pattern", "")
                if (pat.isBlank()) continue
                val regex = try {
                    Regex(pat, setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL))
                } catch (e: Exception) {
                    continue
                }
                out.add(Template(regex, o.optBoolean("is_block", false)))
            }
        } catch (e: Exception) {
            return emptyList()
        }
        return out
    }

    /** Convenience: read + parse the cached templates from Prefs, then decide. */
    fun shouldForward(ctx: android.content.Context, sender: String?, body: String): Boolean =
        shouldForward(sender, body, parseTemplates(Prefs.getTemplatesJson(ctx)))

    fun shouldForward(sender: String?, body: String, templates: List<Template>): Boolean {
        val hay = (sender ?: "") + " " + body

        if (templates.isEmpty()) return legacyHeuristic(hay, body)

        // 1. block templates win.
        if (templates.any { it.isBlock && it.pattern.containsMatchIn(hay) }) return false
        // 2. allow templates.
        if (templates.any { !it.isBlock && it.pattern.containsMatchIn(hay) }) return true
        // 3. fail-open: anything carrying a code is forwarded.
        if (CODE_REGEX.containsMatchIn(body)) return true
        // 4. no code, no match.
        return false
    }

    private fun legacyHeuristic(hay: String, body: String): Boolean {
        if (!CODE_REGEX.containsMatchIn(body)) return false
        val lower = hay.lowercase()
        val companyMatch = COMPANY_KEYWORDS.any { lower.contains(it) }
        val otpMatch = OTP_PHRASES.any { lower.contains(it) }
        return companyMatch || otpMatch
    }
}
