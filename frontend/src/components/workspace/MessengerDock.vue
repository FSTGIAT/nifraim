<template>
  <Teleport to="body">
    <!-- Collapsed: shows WHO'S AROUND at rest, and WHO WANTS YOU when unread. -->
    <Transition name="msgr-pop">
      <button
        v-if="!store.dockOpen"
        class="msgr-pill"
        :class="{ 'msgr-pill--alert': store.totalUnread > 0 }"
        :aria-label="pillLabel"
        @click="store.openDock()"
      >
        <svg class="msgr-pill-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
        </svg>

        <span v-if="store.totalUnread > 0" class="msgr-pill-badge ltr-number">
          {{ store.totalUnread > 99 ? '99+' : store.totalUnread }}
        </span>

        <span v-else-if="onlineFaces.length" class="msgr-pill-faces">
          <Avatar
            v-for="c in onlineFaces.slice(0, 3)"
            :key="c.id"
            class="msgr-face"
            :name="c.full_name"
            :username="c.username"
            :avatar-seed="c.avatar_seed || ''"
            :initial="c.initial"
            :size="24"
          />
        </span>

        <!-- Latin text in an RTL document: pin the direction so it can't reorder. -->
        <span v-else class="msgr-pill-label" dir="ltr">Nifraim friends</span>
      </button>
    </Transition>

    <!-- Expanded -->
    <Transition name="msgr-panel">
      <section v-if="store.dockOpen" class="msgr-panel" role="dialog" aria-label="Nifraim friends" @keydown.esc="onEsc">

        <!-- ── Hero. Tinted block; identity centred; rail lives inside it. ── -->
        <header class="msgr-hero" :class="{ 'msgr-hero--thread': store.openContact }">
          <div class="msgr-hero-top">
            <button
              v-if="store.openContact"
              class="msgr-hero-btn"
              aria-label="חזרה"
              @click="store.closeThread()"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="m9 6 6 6-6 6" />
              </svg>
            </button>
            <button
              v-else
              class="msgr-hero-btn"
              :class="{ 'is-on': settingsOpen }"
              aria-label="הגדרות שם משתמש"
              @click="toggleSettings"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </button>

            <!-- The centred identity: mine on the list, theirs inside a thread. -->
            <div class="msgr-identity">
              <div class="msgr-identity-ring">
                <RemotionAvatarIsland
                  v-if="!store.openContact && me.username"
                  :username="me.username"
                  :avatar-seed="me.avatar_seed || ''"
                  :name="me.full_name"
                  :size="52"
                />
                <Avatar
                  v-else-if="store.openContact"
                  :name="store.openContact.full_name"
                  :username="store.openContact.username"
                  :avatar-seed="store.openContact.avatar_seed || ''"
                  :initial="store.openContact.initial"
                  :online="store.openContact.online"
                  :size="52"
                />
              </div>
              <span class="msgr-identity-name">
                {{ store.openContact
                  ? (store.openContact.full_name || store.openContact.username)
                  : (me.full_name || me.username || 'Nifraim friends') }}
              </span>
              <!-- dir follows the content: a handle is Latin, "מחובר" is not. -->
              <span class="msgr-identity-sub" :dir="subtitle.dir">{{ subtitle.text }}</span>
            </div>

            <button class="msgr-hero-btn" aria-label="סגירה" @click="store.closeDock()">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Search + presence rail, side by side, exactly like the reference:
               a round search affordance leading a scroll of faces. -->
          <div v-if="!store.openContact" class="msgr-hero-rail">
            <div class="msgr-search" :class="{ 'is-wide': searchFocused || store.searchQuery }">
              <button class="msgr-search-btn" aria-label="חיפוש" @click="focusSearch">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <circle cx="11" cy="11" r="7" />
                  <path d="m20 20-3.5-3.5" />
                </svg>
              </button>
              <input
                ref="searchEl"
                :value="store.searchQuery"
                class="msgr-search-input"
                type="search"
                placeholder="חיפוש לפי @שם־משתמש"
                @focus="searchFocused = true"
                @blur="searchFocused = false"
                @input="store.setSearch($event.target.value)"
              />
            </div>

            <div v-if="!store.showingSearch" class="msgr-faces">
              <button
                v-for="c in store.onlineFriends"
                :key="c.id"
                class="msgr-face-btn"
                :title="'@' + c.username"
                @click="store.openThread(c)"
              >
                <Avatar :name="c.full_name" :username="c.username" :avatar-seed="c.avatar_seed || ''" :initial="c.initial" :size="44" online />
              </button>
              <p v-if="!store.onlineFriends.length" class="msgr-faces-none">אף חבר לא מחובר כרגע</p>
            </div>
          </div>
        </header>

        <!-- ── White sheet, lifted over the hero's bottom edge. ── -->
        <div class="msgr-sheet">
          <MessengerThread v-if="store.openContact" :contact="store.openContact" />

          <template v-else>
            <Transition name="msgr-settings">
              <form v-if="settingsOpen" class="msgr-settings" @submit.prevent="saveUsername">
                <!-- Avatar picker. Each swatch is the real gradient for that
                     seed (shared math), so what you tap is what you get. -->
                <p class="msgr-settings-label">האווטאר שלך</p>
                <p class="msgr-settings-hint">בחרו מראה. כל מי שמתכתב איתכם יראה אותו.</p>
                <div class="msgr-avatars" role="radiogroup" aria-label="בחירת אווטאר">
                  <button
                    v-for="s in avatarChoices"
                    :key="s"
                    type="button"
                    class="msgr-avatar-swatch"
                    :class="{ 'is-picked': s === currentSeed }"
                    role="radio"
                    :aria-checked="s === currentSeed"
                    :aria-label="'אווטאר ' + s"
                    @click="pickAvatar(s)"
                  >
                    <Avatar
                      :avatar-seed="s"
                      :username="me.username"
                      :name="me.full_name"
                      :size="40"
                    />
                  </button>
                </div>
                <p v-if="avatarError" class="msgr-settings-error">{{ avatarError }}</p>

                <hr class="msgr-settings-rule" />

                <label class="msgr-settings-label" for="msgr-handle">שם המשתמש שלך</label>
                <p class="msgr-settings-hint">כך חברים ימצאו אתכם. 3–32 תווים: אותיות אנגליות קטנות, ספרות וקו תחתון.</p>
                <div class="msgr-settings-row">
                  <!-- LTR wrapper so the "@" hugs the handle instead of being
                       flung to the far edge by the RTL row. -->
                  <div class="msgr-handle-field" dir="ltr">
                    <span class="msgr-at" aria-hidden="true">@</span>
                    <input
                      id="msgr-handle"
                      v-model="handleDraft"
                      class="msgr-settings-input"
                      type="text"
                      maxlength="32"
                      autocomplete="off"
                      spellcheck="false"
                    />
                  </div>
                  <button type="submit" class="msgr-settings-save" :disabled="saving || handleDraft === me.username">
                    {{ saving ? 'שומר…' : 'שמירה' }}
                  </button>
                </div>
                <p v-if="handleError" class="msgr-settings-error">{{ handleError }}</p>
                <p v-else-if="handleSaved" class="msgr-settings-ok">שם המשתמש עודכן</p>
              </form>
            </Transition>

            <p v-if="store.searching" class="msgr-empty">מחפש…</p>

            <p v-else-if="store.showingSearch && !store.searchResults.length" class="msgr-empty">
              לא נמצא משתמש בשם «{{ store.searchQuery }}»
            </p>

            <p v-else-if="!store.showingSearch && !store.contacts.length" class="msgr-empty">
              אין עדיין שיחות.<br />חפשו לפי שם משתמש כדי להתחיל.
            </p>

            <ul v-else class="msgr-rows">
              <li v-for="c in store.listedContacts" :key="c.id" class="msgr-row-wrap">
                <!-- Confirm before destroying anything: never delete on one click. -->
                <div v-if="confirmingId === c.id" class="msgr-confirm">
                  <span class="msgr-confirm-text">למחוק את השיחה?</span>
                  <button class="msgr-confirm-no" @click.stop="confirmingId = null">ביטול</button>
                  <button class="msgr-confirm-yes" @click.stop="doDelete(c)">מחיקה</button>
                </div>

                <button class="msgr-row" :class="{ 'is-unread': c.unread > 0 }" @click="store.openThread(c)">
                  <Avatar :name="c.full_name" :username="c.username" :avatar-seed="c.avatar_seed || ''" :initial="c.initial" :online="c.online" :size="46" />

                  <span class="msgr-row-mid">
                    <span class="msgr-row-name">{{ c.full_name || c.username }}</span>
                    <span class="msgr-row-preview">
                      <template v-if="c.last_message_preview">
                        <span v-if="c.last_message_from_me" class="msgr-row-you">את/ה:</span>
                        {{ c.last_message_preview }}
                      </template>
                      <template v-else>@{{ c.username }}</template>
                    </span>
                  </span>

                  <span class="msgr-row-end">
                    <span v-if="c.last_message_at" class="msgr-row-time ltr-number">{{ shortTime(c.last_message_at) }}</span>
                    <span v-if="c.unread" class="msgr-row-badge ltr-number">{{ c.unread }}</span>
                  </span>
                </button>

                <!-- Sibling, not nested: a <button> inside a <button> is invalid
                     and swallows the click. Only for real conversations. -->
                <button
                  v-if="!store.showingSearch"
                  class="msgr-row-del"
                  :aria-label="'מחיקת השיחה עם ' + (c.full_name || c.username)"
                  @click.stop="confirmingId = c.id"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14" />
                  </svg>
                </button>
              </li>
            </ul>
          </template>
        </div>
      </section>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import Avatar from '../Avatar.vue'
import RemotionAvatarIsland from './RemotionAvatarIsland.vue'
import MessengerThread from './MessengerThread.vue'
import { useMessengerStore } from '../../stores/messenger.js'
import { useAuthStore } from '../../stores/auth.js'
import { candidateSeeds, seedFor } from '../../utils/avatarSeed.js'

const store = useMessengerStore()
const auth = useAuthStore()

const me = computed(() => auth.user || {})

// The pill shows who's around at rest — from /messenger/online, not just people
// I've already talked to.
const onlineFaces = computed(() => store.onlineFriends)

const pillLabel = computed(() =>
  store.totalUnread > 0 ? `Nifraim friends — ${store.totalUnread} הודעות חדשות` : 'Nifraim friends'
)

// The line under the name: their status inside a thread, my handle on the list.
const subtitle = computed(() => {
  const c = store.openContact
  if (c) {
    return c.online
      ? { text: 'מחובר', dir: 'rtl' }
      : { text: `@${c.username}`, dir: 'ltr' }
  }
  return { text: `@${me.value.username || ''}`, dir: 'ltr' }
})

const searchEl = ref(null)
const searchFocused = ref(false)
function focusSearch () { searchEl.value?.focus() }

function shortTime (iso) {
  const d = new Date(iso)
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  if (sameDay) return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  return `${d.getDate()}/${d.getMonth() + 1}`
}

// Avatar picker. The first candidate is the bare username, so "never chose" and
// "chose the default" render the same face.
const avatarChoices = computed(() => candidateSeeds(me.value.username || ''))
const currentSeed = computed(() => seedFor(me.value))
const avatarError = ref('')

async function pickAvatar (seed) {
  if (seed === currentSeed.value) return
  avatarError.value = ''
  try {
    await store.changeAvatar(seed)
  } catch {
    avatarError.value = 'שמירת האווטאר נכשלה'
  }
}

// Deleting a conversation only clears MY copy — the other person keeps theirs.
const confirmingId = ref(null)
async function doDelete (contact) {
  const id = contact.id
  confirmingId.value = null
  try {
    await store.deleteThread(id)
  } catch {
    store.error = 'מחיקת השיחה נכשלה'
  }
}

const settingsOpen = ref(false)
const handleDraft = ref('')
const handleError = ref('')
const handleSaved = ref(false)
const saving = ref(false)

function toggleSettings () {
  settingsOpen.value = !settingsOpen.value
  if (settingsOpen.value) {
    handleDraft.value = me.value.username || ''
    handleError.value = ''
    handleSaved.value = false
    nextTick(() => document.getElementById('msgr-handle')?.focus())
  }
}

async function saveUsername () {
  handleError.value = ''
  handleSaved.value = false
  saving.value = true
  try {
    await store.changeUsername(handleDraft.value)
    handleSaved.value = true
    await store.fetchContacts().catch(() => {})
  } catch (e) {
    handleError.value = e.message
  } finally {
    saving.value = false
  }
}

// Opening a thread hides the settings form — it belongs to the contacts view.
watch(() => store.openContact, (c) => { if (c) settingsOpen.value = false })

function onEsc () {
  if (confirmingId.value) confirmingId.value = null
  else if (settingsOpen.value) settingsOpen.value = false
  else if (store.openContact) store.closeThread()
  else store.closeDock()
}
</script>

<style scoped>
/*
  Positioning. The app root is dir="rtl" (index.html) and body { direction: rtl }
  (App.vue), and this Teleports into <body> — so `inset-inline-start` resolves to
  the physical RIGHT edge. That is the one free corner: bottom-centre is
  PortalRunProgressFloat (z 2000), bottom-left is BatchResultsToast (z 1300),
  top-left is NotificationBell. Never use inset-inline-end here.
  z-index 1400 sits in the free 1300–1600 band.
*/
.msgr-pill,
.msgr-panel {
  position: fixed;
  bottom: 20px;
  inset-inline-start: 20px;
  z-index: 1400;
}

/* ---------------------------------------------------------------- the pill */
.msgr-pill {
  height: 52px;
  padding: 0 14px;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--chart-11), #E23E73);
  color: #fff;
  font: inherit;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
  box-shadow: var(--shadow-lg);
  transition: transform 0.18s var(--transition), box-shadow 0.18s var(--transition);
}
.msgr-pill:hover { transform: translateY(-2px); box-shadow: 0 8px 22px rgba(226, 62, 115, 0.34); }
.msgr-pill:focus-visible { outline: 3px solid rgba(255, 92, 138, 0.45); outline-offset: 2px; }
.msgr-pill-icon { width: 21px; height: 21px; flex-shrink: 0; }
.msgr-pill-label { padding-inline-end: 2px; }

.msgr-pill-badge {
  min-width: 20px; height: 20px; padding: 0 6px;
  border-radius: 999px;
  background: #fff; color: #E23E73;
  font-size: 11px; font-weight: 800;
  display: grid; place-items: center;
}

.msgr-pill-faces { display: inline-flex; }
.msgr-face { box-shadow: 0 0 0 2px #E23E73; }
.msgr-face + .msgr-face { margin-inline-start: -9px; }

.msgr-pill--alert { animation: msgrNudge 3.2s ease-in-out infinite; }
@keyframes msgrNudge {
  0%, 88%, 100% { transform: translateY(0); }
  92% { transform: translateY(-3px); }
  96% { transform: translateY(-1px); }
}

/* --------------------------------------------------------------- the panel */
.msgr-panel {
  width: 380px;
  max-width: calc(100vw - 40px);
  height: 600px;
  max-height: calc(100vh - 40px);
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
  box-shadow: 0 18px 50px rgba(24, 24, 24, 0.22), 0 2px 8px rgba(24, 24, 24, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ------------------------------------------------------------------- hero */
.msgr-hero {
  flex-shrink: 0;
  position: relative;
  padding: 16px 14px 26px;
  background:
    radial-gradient(120% 80% at 78% 0%, rgba(255, 255, 255, 0.20) 0%, rgba(255, 255, 255, 0) 55%),
    linear-gradient(150deg, #FF7AA2 0%, var(--chart-11) 42%, #D8356B 100%);
  color: #fff;
}
.msgr-hero--thread { padding-bottom: 22px; }

.msgr-hero-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.msgr-hero-btn {
  flex-shrink: 0;
  width: 34px; height: 34px;
  display: grid; place-items: center;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  cursor: pointer;
  transition: background 0.16s var(--transition);
}
.msgr-hero-btn svg { width: 17px; height: 17px; }
.msgr-hero-btn:hover { background: rgba(255, 255, 255, 0.28); }
.msgr-hero-btn.is-on { background: #fff; color: #D8356B; }
.msgr-hero-btn:focus-visible { outline: 2px solid #fff; outline-offset: 2px; }

/* The identity block — centred between the two round buttons. */
.msgr-identity {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  margin-top: -2px;
}
.msgr-identity-ring {
  width: 60px; height: 60px;
  display: grid; place-items: center;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.18);
  box-shadow: 0 4px 14px rgba(120, 20, 55, 0.28);
  margin-bottom: 5px;
}
.msgr-identity-name {
  max-width: 100%;
  font-size: 14px; font-weight: 800; letter-spacing: 0.01em;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.msgr-identity-sub {
  font-size: 11px; font-weight: 600;
  color: rgba(255, 255, 255, 0.78);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;
}

/* Search + faces, one scrolling row. */
.msgr-hero-rail {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
}

.msgr-search {
  flex-shrink: 0;
  display: flex; align-items: center;
  width: 44px;
  height: 44px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  overflow: hidden;
  transition: width 0.24s var(--transition), background 0.24s var(--transition);
}
.msgr-search.is-wide { width: 100%; background: rgba(255, 255, 255, 0.26); }
.msgr-search-btn {
  flex-shrink: 0;
  width: 44px; height: 44px;
  display: grid; place-items: center;
  border: none; background: none; color: #fff; cursor: pointer;
}
.msgr-search-btn svg { width: 18px; height: 18px; }
.msgr-search-input {
  flex: 1; min-width: 0;
  border: none; background: none;
  font: inherit; font-size: 12.5px; color: #fff;
  padding-inline-end: 12px;
}
.msgr-search-input::placeholder { color: rgba(255, 255, 255, 0.72); }
.msgr-search-input:focus { outline: none; }
.msgr-search-input::-webkit-search-cancel-button { filter: invert(1); }

.msgr-faces {
  display: flex; align-items: center; gap: 9px;
  overflow-x: auto;
  scrollbar-width: none;
  min-height: 44px;
}
.msgr-faces::-webkit-scrollbar { display: none; }
.msgr-face-btn {
  flex-shrink: 0;
  border: none; background: none; padding: 0; cursor: pointer;
  border-radius: 50%;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.85);
  transition: transform 0.16s var(--transition);
}
.msgr-face-btn:hover { transform: translateY(-2px); }
.msgr-faces-none { margin: 0; font-size: 11.5px; color: rgba(255, 255, 255, 0.8); white-space: nowrap; }

/* ------------------------------------------------------------------ sheet */
.msgr-sheet {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-surface);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  margin-top: -18px;   /* lift the sheet over the hero's bottom edge */
  position: relative;
  z-index: 1;
  overflow: hidden;
}

.msgr-empty {
  margin: auto; padding: 24px;
  text-align: center; font-size: 12.5px; line-height: 1.7; color: var(--text-muted);
}

/* -------------------------------------------------------------- row list */
.msgr-rows { flex: 1; min-height: 0; overflow-y: auto; list-style: none; margin: 0; padding: 10px 0 6px; }
.msgr-row-wrap { position: relative; }
.msgr-row {
  width: 100%;
  display: flex; align-items: center; gap: 11px;
  padding: 9px 16px;
  border: none; background: none; cursor: pointer;
  text-align: start; font: inherit;
}
.msgr-row:hover { background: var(--bg); }

/* Trash sits over the row's inline-end edge; revealed on hover/focus, and
   always visible on touch where there is no hover. */
.msgr-row-del {
  position: absolute;
  inset-block-start: 50%;
  inset-inline-end: 6px;
  transform: translateY(-50%);
  width: 28px; height: 28px;
  display: grid; place-items: center;
  border: none; border-radius: 50%;
  background: var(--bg-surface);
  color: var(--text-muted);
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.14s var(--transition), color 0.14s var(--transition);
}
.msgr-row-del svg { width: 15px; height: 15px; }
.msgr-row-wrap:hover .msgr-row-del,
.msgr-row-del:focus-visible { opacity: 1; }
.msgr-row-del:hover { color: #B3261E; background: #FDECEA; }
@media (hover: none) { .msgr-row-del { opacity: 1; } }

.msgr-confirm {
  position: absolute; inset: 0;
  z-index: 2;
  display: flex; align-items: center; gap: 8px;
  padding: 0 14px;
  background: var(--bg-surface);
  border-block: 1px solid var(--border-subtle);
}
.msgr-confirm-text { flex: 1; font-size: 12.5px; font-weight: 700; color: var(--text); }
.msgr-confirm-no, .msgr-confirm-yes {
  flex-shrink: 0;
  border: none; border-radius: var(--radius-sm);
  padding: 6px 12px;
  font: inherit; font-size: 12px; font-weight: 700; cursor: pointer;
}
.msgr-confirm-no { background: var(--bg); color: var(--text-secondary); }
.msgr-confirm-yes { background: #B3261E; color: #fff; }

.msgr-row-mid { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.msgr-row-name {
  font-size: 13.5px; font-weight: 600; color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.msgr-row.is-unread .msgr-row-name { color: var(--chart-11); font-weight: 800; }
.msgr-row-preview {
  font-size: 11.5px; color: var(--text-muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.msgr-row.is-unread .msgr-row-preview { color: var(--text-secondary); font-weight: 600; }
.msgr-row-you { color: var(--text-secondary); font-weight: 600; }

/* Time + unread stack at the inline END (physical left under RTL), mirroring
   the reference's right-hand column. */
.msgr-row-end {
  flex-shrink: 0;
  display: flex; flex-direction: column; align-items: center; gap: 5px;
  min-width: 34px;
}
.msgr-row-time { font-size: 10.5px; color: var(--text-muted); }
.msgr-row-badge {
  min-width: 19px; height: 19px; padding: 0 5px;
  border-radius: 999px;
  background: var(--chart-11); color: #fff;
  font-size: 10.5px; font-weight: 800;
  display: grid; place-items: center;
  box-shadow: 0 2px 6px rgba(226, 62, 115, 0.4);
}

/* ------------------------------------------------------- username settings */
.msgr-settings {
  flex-shrink: 0;
  margin: 12px 14px 4px;
  padding: 12px;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.msgr-settings-label { display: block; margin: 0; font-size: 12.5px; font-weight: 700; color: var(--text); }
.msgr-settings-hint { margin: 3px 0 8px; font-size: 11px; line-height: 1.5; color: var(--text-muted); }
.msgr-settings-rule { border: none; border-top: 1px solid var(--border-subtle); margin: 12px 0; }

/* -------------------------------------------------------- avatar picker */
/* 4×2 rather than 8×1: eight 40px swatches plus borders overflow 380px. */
.msgr-avatars {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  justify-items: center;
}
.msgr-avatar-swatch {
  display: grid; place-items: center;
  padding: 2px;
  border: 2px solid transparent;
  border-radius: 50%;
  background: none;
  cursor: pointer;
  transition: transform 0.16s var(--transition), border-color 0.16s var(--transition);
}
.msgr-avatar-swatch:hover { transform: scale(1.1); }
.msgr-avatar-swatch.is-picked { border-color: var(--chart-11); }
.msgr-avatar-swatch:focus-visible { outline: 2px solid var(--chart-11); outline-offset: 1px; }

.msgr-settings-row {
  display: flex; align-items: center; gap: 6px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 4px;
  padding-inline-start: 9px;
}
.msgr-settings-row:focus-within { border-color: var(--chart-11); }
.msgr-handle-field { flex: 1; min-width: 0; display: flex; align-items: center; gap: 2px; }
.msgr-at { font-size: 13px; font-weight: 700; color: var(--text-muted); }
.msgr-settings-input {
  flex: 1; min-width: 0;
  border: none; background: none; font: inherit; font-size: 13px; color: var(--text);
}
.msgr-settings-input:focus { outline: none; }
.msgr-settings-save {
  flex-shrink: 0;
  border: none; border-radius: var(--radius-sm);
  padding: 6px 12px;
  background: linear-gradient(135deg, var(--chart-11), #E23E73);
  color: #fff; font: inherit; font-size: 12px; font-weight: 700; cursor: pointer;
}
.msgr-settings-save:disabled { opacity: 0.45; cursor: default; }
.msgr-settings-error { margin: 7px 0 0; font-size: 11.5px; color: #B3261E; }
.msgr-settings-ok { margin: 7px 0 0; font-size: 11.5px; color: var(--green); }

.msgr-settings-enter-active, .msgr-settings-leave-active { transition: opacity 0.18s var(--transition); }
.msgr-settings-enter-from, .msgr-settings-leave-to { opacity: 0; }

/* ------------------------------------------------------------- transitions */
.msgr-pop-enter-active, .msgr-pop-leave-active { transition: transform 0.2s var(--transition), opacity 0.2s var(--transition); }
.msgr-pop-enter-from, .msgr-pop-leave-to { transform: scale(0.86) translateY(8px); opacity: 0; }

.msgr-panel-enter-active, .msgr-panel-leave-active { transition: transform 0.24s var(--transition), opacity 0.24s var(--transition); }
.msgr-panel-enter-from, .msgr-panel-leave-to { transform: translateY(16px) scale(0.97); opacity: 0; transform-origin: bottom right; }

/* -------------------------------------------------------------- mobile */
@media (max-width: 520px) {
  .msgr-panel {
    inset-inline: 0;
    bottom: 0;
    width: auto;
    max-width: none;
    height: 86vh;
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .msgr-pill, .msgr-pill--alert, .msgr-search, .msgr-face-btn,
  .msgr-pop-enter-active, .msgr-pop-leave-active,
  .msgr-panel-enter-active, .msgr-panel-leave-active { transition: none; animation: none; }
}
</style>
