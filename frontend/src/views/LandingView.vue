<template>
  <div class="landing">
    <!-- Nav -->
    <nav class="landing-nav">
      <div class="nav-content">
        <div class="nav-brand">
          <div class="nav-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <span class="nav-name">Nifraim</span>
        </div>
        <div class="nav-links">
          <a href="#features">תכונות</a>
          <a href="#how-it-works">איך זה עובד</a>
          <a href="#demo">הדגמה</a>
          <router-link to="/pricing" class="nav-link-pricing">תמחור</router-link>
          <router-link to="/login" class="nav-btn-secondary">התחברות</router-link>
          <router-link to="/signup" class="nav-btn-primary">התחל עכשיו</router-link>
        </div>
      </div>
    </nav>

    <!-- Hero -->
    <section class="hero">
      <div class="hero-content">
        <div class="hero-badge">מערכת נפרעים חכמה לסוכני ביטוח</div>
        <h1>נהלו את העמלות שלכם<br>בצורה <span class="gradient-text">חכמה ומדויקת</span></h1>
        <p class="hero-subtitle">
          העלו קבצי אקסל מחברות הביטוח, השוו מול הפרודוקציה,
          וגלו פערי עמלות תוך שניות. לא עוד אקסלים אינסופיים.
        </p>
        <div class="hero-actions">
          <router-link to="/signup" class="btn-hero-primary">
            התחילו בחינם
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="19" y1="12" x2="5" y2="12"/>
              <polyline points="12 5 5 12 12 19"/>
            </svg>
          </router-link>
          <a href="#demo" class="btn-hero-secondary">צפו בהדגמה</a>
        </div>
        <div class="hero-stats">
          <div class="stat">
            <span class="stat-number ltr-number">95%</span>
            <span class="stat-label">חיסכון בזמן</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-number ltr-number">7+</span>
            <span class="stat-label">פורמטים נתמכים</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-number ltr-number">100%</span>
            <span class="stat-label">דיוק בהשוואה</span>
          </div>
        </div>
      </div>
      <div class="hero-visual">
        <div class="dashboard-mockup">
          <div class="mockup-header">
            <div class="mockup-dots">
              <span></span><span></span><span></span>
            </div>
            <span class="mockup-title">Nifraim Dashboard</span>
          </div>
          <div class="mockup-body">
            <div class="mockup-sidebar">
              <div class="mockup-nav-item active"></div>
              <div class="mockup-nav-item"></div>
              <div class="mockup-nav-item"></div>
              <div class="mockup-nav-item"></div>
            </div>
            <div class="mockup-main">
              <div class="mockup-cards">
                <div class="mockup-card green">
                  <span class="mockup-card-label">תואם</span>
                  <span class="mockup-card-value ltr-number">{{ animatedMatched }}</span>
                </div>
                <div class="mockup-card amber">
                  <span class="mockup-card-label">חסר</span>
                  <span class="mockup-card-value ltr-number">{{ animatedMissing }}</span>
                </div>
                <div class="mockup-card red">
                  <span class="mockup-card-label">פער עמלה</span>
                  <span class="mockup-card-value ltr-number">{{ animatedGap }}</span>
                </div>
              </div>
              <div class="mockup-chart">
                <div class="mockup-bar" v-for="(h, i) in barHeights" :key="i" :style="{ height: h + '%' }"></div>
              </div>
              <div class="mockup-table">
                <div class="mockup-row" v-for="i in 4" :key="i"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Features -->
    <section id="features" class="features">
      <div class="section-content">
        <div class="section-header">
          <h2>הכלים שלכם להצלחה</h2>
          <p>כל מה שצריך כדי לנהל עמלות ביטוח בצורה מקצועית</p>
        </div>
        <div class="features-grid">
          <div class="feature-card" v-for="(f, i) in features" :key="i">
            <div class="feature-icon" :class="f.color">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" v-html="f.iconPath"></svg>
            </div>
            <h3>{{ f.title }}</h3>
            <p>{{ f.description }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- How It Works -->
    <section id="how-it-works" class="how-it-works">
      <div class="section-content">
        <div class="section-header">
          <h2>איך זה עובד?</h2>
          <p>שלושה צעדים פשוטים לניהול עמלות מושלם</p>
        </div>
        <div class="steps">
          <div class="step" v-for="(s, i) in steps" :key="i">
            <div class="step-number ltr-number">{{ i + 1 }}</div>
            <h3>{{ s.title }}</h3>
            <p>{{ s.description }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Demo -->
    <section id="demo" class="demo-section">
      <div class="section-content">
        <div class="section-header">
          <h2>ראו את זה בפעולה</h2>
          <p>הנה איך נראית השוואת נפרעים במערכת</p>
        </div>
        <div class="demo-window">
          <div class="demo-header">
            <div class="mockup-dots"><span></span><span></span><span></span></div>
            <span>השוואת נפרעים — אקסלנס גמל</span>
          </div>
          <div class="demo-body">
            <div class="demo-summary">
              <div class="demo-stat green">
                <div class="demo-stat-value ltr-number">208</div>
                <div class="demo-stat-label">תואם - תשלום</div>
              </div>
              <div class="demo-stat amber">
                <div class="demo-stat-value ltr-number">364</div>
                <div class="demo-stat-label">תואם - פער</div>
              </div>
              <div class="demo-stat red">
                <div class="demo-stat-value ltr-number">77</div>
                <div class="demo-stat-label">לא שולם</div>
              </div>
              <div class="demo-stat gray">
                <div class="demo-stat-value ltr-number">85</div>
                <div class="demo-stat-label">חסר בנפרעים</div>
              </div>
            </div>
            <div class="demo-table">
              <div class="demo-table-header">
                <span>שם לקוח</span>
                <span>ת.ז.</span>
                <span>מוצר</span>
                <span>סטטוס</span>
              </div>
              <div class="demo-table-row" v-for="(r, i) in demoRows" :key="i">
                <span>{{ r.name }}</span>
                <span class="ltr-number">{{ r.id }}</span>
                <span>{{ r.product }}</span>
                <span class="demo-badge" :class="r.statusClass">{{ r.status }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta-section">
      <div class="section-content">
        <h2>מוכנים להתחיל?</h2>
        <p>הצטרפו למאות סוכני ביטוח שכבר חוסכים שעות של עבודה</p>
        <div class="cta-actions">
          <router-link to="/pricing" class="btn-hero-primary">צפו בתמחור</router-link>
          <router-link to="/signup" class="btn-hero-secondary">הרשמה חינם</router-link>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="landing-footer">
      <div class="footer-content">
        <div class="footer-brand">
          <div class="nav-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <span>Nifraim</span>
        </div>
        <p class="footer-text">מערכת ניהול עמלות ביטוח מתקדמת</p>
        <p class="footer-copy ltr-number">&copy; 2026 Nifraim. All rights reserved.</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const animatedMatched = ref(0)
const animatedMissing = ref(0)
const animatedGap = ref(0)
const barHeights = ref([20, 35, 50, 70, 45, 60, 80, 55, 40, 65])

const features = [
  {
    title: 'פרסור אקסל חכם',
    description: 'זיהוי אוטומטי של 7+ פורמטים מחברות ביטוח שונות, כולל קבצים מוגני סיסמא.',
    color: 'blue',
    iconPath: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
  },
  {
    title: 'השוואת נפרעים',
    description: 'התאמה אוטומטית בין פרודוקציה לנפרעים. זיהוי פערים, חסרים ואי-התאמות.',
    color: 'green',
    iconPath: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
  },
  {
    title: 'חיסכון בזמן',
    description: 'מה שלקח שעות באקסל — לוקח שניות. העלו קבצים וקבלו תוצאות מיידיות.',
    color: 'amber',
    iconPath: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  },
  {
    title: 'מולטי-חברה',
    description: 'תמיכה באקסלנס, הפניקס, מור, הכשרה, מנורה, אלטשולר ועוד.',
    color: 'violet',
    iconPath: '<rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
  },
]

const steps = [
  { title: 'העלו פרודוקציה', description: 'גררו את קובץ הפרודוקציה מהסוכנות אל המערכת. זיהוי אוטומטי של הפורמט.' },
  { title: 'השוו נפרעים', description: 'העלו דוח נפרעים מחברת הביטוח. המערכת מתאימה רשומות לפי ת.ז. ומספר פוליסה.' },
  { title: 'קבלו תובנות', description: 'צפו בתוצאות: מי שולם, מי לא, היכן יש פערים — והפיקו דוחות לבירור.' },
]

const demoRows = [
  { name: 'ישראל ישראלי', id: '123456789', product: 'גמל', status: 'תואם', statusClass: 'green' },
  { name: 'שרה כהן', id: '987654321', product: 'פנסיה', status: 'פער עמלה', statusClass: 'amber' },
  { name: 'דוד לוי', id: '456789123', product: 'ביטוח חיים', status: 'לא שולם', statusClass: 'red' },
  { name: 'רחל אברהם', id: '321654987', product: 'גמל', status: 'חסר', statusClass: 'gray' },
]

function animateCounter(target, finalValue, duration = 1500) {
  const start = performance.now()
  function tick(now) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    target.value = Math.round(finalValue * eased)
    if (progress < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

onMounted(() => {
  setTimeout(() => {
    animateCounter(animatedMatched, 208)
    animateCounter(animatedMissing, 77)
    animateCounter(animatedGap, 364)
  }, 600)
})
</script>

<style scoped>
.landing {
  min-height: 100vh;
  background: var(--bg);
}

/* ── Nav ── */
.landing-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
}

.nav-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.nav-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-cyan) 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.nav-name {
  font-size: 20px;
  font-weight: 800;
  color: var(--text);
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 24px;
}

.nav-links a {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  transition: color 0.2s;
}

.nav-links a:hover {
  color: var(--primary);
}

.nav-btn-secondary {
  padding: 8px 20px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border) !important;
  font-weight: 600 !important;
  color: var(--text) !important;
  transition: all 0.2s;
}

.nav-btn-secondary:hover {
  border-color: var(--primary) !important;
  color: var(--primary) !important;
}

.nav-btn-primary {
  padding: 8px 20px;
  border-radius: var(--radius-sm);
  background: var(--primary) !important;
  color: white !important;
  font-weight: 600 !important;
  transition: all 0.2s;
}

.nav-btn-primary:hover {
  background: var(--primary-deep) !important;
}

/* ── Hero ── */
.hero {
  padding: 140px 24px 80px;
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 60px;
  align-items: center;
}

.hero-badge {
  display: inline-block;
  padding: 6px 16px;
  background: var(--primary-light);
  color: var(--primary);
  border-radius: 100px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 24px;
  animation: fadeInUp 0.6s var(--transition);
}

.hero h1 {
  font-size: 48px;
  font-weight: 900;
  line-height: 1.15;
  color: var(--text);
  margin-bottom: 20px;
  animation: fadeInUp 0.6s var(--transition) 0.1s both;
}

.gradient-text {
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-cyan) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: 18px;
  color: var(--text-muted);
  line-height: 1.6;
  max-width: 500px;
  margin-bottom: 32px;
  animation: fadeInUp 0.6s var(--transition) 0.2s both;
}

.hero-actions {
  display: flex;
  gap: 16px;
  margin-bottom: 48px;
  animation: fadeInUp 0.6s var(--transition) 0.3s both;
}

.btn-hero-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 32px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-cyan) 100%);
  color: white !important;
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 700;
  transition: all 0.3s var(--transition);
  box-shadow: 0 4px 16px rgba(1, 118, 211, 0.3);
}

.btn-hero-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(1, 118, 211, 0.4);
}

.btn-hero-secondary {
  display: inline-flex;
  align-items: center;
  padding: 14px 32px;
  background: var(--bg-surface);
  color: var(--text) !important;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-hero-secondary:hover {
  border-color: var(--primary);
  color: var(--primary) !important;
}

.hero-stats {
  display: flex;
  align-items: center;
  gap: 24px;
  animation: fadeInUp 0.6s var(--transition) 0.4s both;
}

.stat {
  text-align: center;
}

.stat-number {
  display: block;
  font-size: 28px;
  font-weight: 800;
  color: var(--primary);
}

.stat-label {
  font-size: 13px;
  color: var(--text-muted);
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: var(--border);
}

/* ── Dashboard Mockup ── */
.hero-visual {
  animation: fadeInUp 0.8s var(--transition) 0.3s both;
}

.dashboard-mockup {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}

.mockup-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
}

.mockup-dots {
  display: flex;
  gap: 6px;
}

.mockup-dots span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--border);
}

.mockup-dots span:first-child { background: #EA001E; }
.mockup-dots span:nth-child(2) { background: #E8720A; }
.mockup-dots span:last-child { background: #2E844A; }

.mockup-title {
  font-size: 12px;
  color: var(--text-muted);
}

.mockup-body {
  display: flex;
  padding: 16px;
  gap: 16px;
  min-height: 280px;
}

.mockup-sidebar {
  width: 48px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mockup-nav-item {
  height: 8px;
  border-radius: 4px;
  background: var(--border);
}

.mockup-nav-item.active {
  background: var(--primary);
}

.mockup-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mockup-cards {
  display: flex;
  gap: 10px;
}

.mockup-card {
  flex: 1;
  padding: 12px;
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mockup-card.green { background: var(--green-light); }
.mockup-card.amber { background: var(--amber-light); }
.mockup-card.red { background: var(--red-light); }

.mockup-card-label {
  font-size: 10px;
  color: var(--text-muted);
}

.mockup-card-value {
  font-size: 22px;
  font-weight: 800;
}

.mockup-card.green .mockup-card-value { color: var(--green); }
.mockup-card.amber .mockup-card-value { color: var(--amber); }
.mockup-card.red .mockup-card-value { color: var(--red); }

.mockup-chart {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  height: 80px;
  padding: 8px 0;
}

.mockup-bar {
  flex: 1;
  background: linear-gradient(180deg, var(--primary) 0%, rgba(1, 118, 211, 0.3) 100%);
  border-radius: 4px 4px 0 0;
  transition: height 1s var(--transition);
}

.mockup-table {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mockup-row {
  height: 12px;
  background: var(--bg);
  border-radius: 4px;
}

.mockup-row:nth-child(odd) { width: 90%; }

/* ── Sections ── */
.section-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.section-header {
  text-align: center;
  margin-bottom: 48px;
}

.section-header h2 {
  font-size: 36px;
  font-weight: 800;
  color: var(--text);
  margin-bottom: 12px;
}

.section-header p {
  font-size: 18px;
  color: var(--text-muted);
}

/* ── Features ── */
.features {
  padding: 100px 24px;
  background: var(--bg-surface);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.feature-card {
  padding: 32px 24px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  transition: all 0.3s var(--transition);
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.feature-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.feature-icon.blue { background: var(--primary-light); color: var(--primary); }
.feature-icon.green { background: var(--green-light); color: var(--green); }
.feature-icon.amber { background: var(--amber-light); color: var(--amber); }
.feature-icon.violet { background: rgba(127, 86, 217, 0.1); color: var(--accent-violet); }

.feature-card h3 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
}

.feature-card p {
  font-size: 14px;
  color: var(--text-muted);
  line-height: 1.6;
}

/* ── How It Works ── */
.how-it-works {
  padding: 100px 24px;
}

.steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 40px;
}

.step {
  text-align: center;
  padding: 24px;
}

.step-number {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-cyan) 100%);
  color: white;
  font-size: 24px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
}

.step h3 {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 8px;
  color: var(--text);
}

.step p {
  font-size: 15px;
  color: var(--text-muted);
  line-height: 1.6;
}

/* ── Demo ── */
.demo-section {
  padding: 100px 24px;
  background: var(--bg-surface);
}

.demo-window {
  max-width: 900px;
  margin: 0 auto;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}

.demo-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  font-size: 13px;
  color: var(--text-muted);
}

.demo-body {
  padding: 24px;
  background: var(--card-bg);
}

.demo-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.demo-stat {
  padding: 16px;
  border-radius: var(--radius-sm);
  text-align: center;
}

.demo-stat.green { background: var(--green-light); }
.demo-stat.amber { background: var(--amber-light); }
.demo-stat.red { background: var(--red-light); }
.demo-stat.gray { background: var(--bg); }

.demo-stat-value {
  font-size: 28px;
  font-weight: 800;
}

.demo-stat.green .demo-stat-value { color: var(--green); }
.demo-stat.amber .demo-stat-value { color: var(--amber); }
.demo-stat.red .demo-stat-value { color: var(--red); }
.demo-stat.gray .demo-stat-value { color: var(--text-muted); }

.demo-stat-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.demo-table {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.demo-table-header {
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr 1fr;
  padding: 10px 16px;
  background: var(--bg);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border);
}

.demo-table-row {
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr 1fr;
  padding: 12px 16px;
  font-size: 14px;
  border-bottom: 1px solid var(--border-subtle);
}

.demo-table-row:last-child {
  border-bottom: none;
}

.demo-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 600;
}

.demo-badge.green { background: var(--green-light); color: var(--green); }
.demo-badge.amber { background: var(--amber-light); color: var(--amber); }
.demo-badge.red { background: var(--red-light); color: var(--red); }
.demo-badge.gray { background: var(--bg); color: var(--text-muted); }

/* ── CTA ── */
.cta-section {
  padding: 100px 24px;
  text-align: center;
}

.cta-section h2 {
  font-size: 36px;
  font-weight: 800;
  margin-bottom: 12px;
}

.cta-section p {
  font-size: 18px;
  color: var(--text-muted);
  margin-bottom: 32px;
}

.cta-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
}

/* ── Footer ── */
.landing-footer {
  padding: 48px 24px;
  border-top: 1px solid var(--border);
  background: var(--bg-surface);
}

.footer-content {
  max-width: 1200px;
  margin: 0 auto;
  text-align: center;
}

.footer-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
}

.footer-text {
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.footer-copy {
  font-size: 12px;
  color: var(--text-muted);
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .hero {
    grid-template-columns: 1fr;
    padding-top: 100px;
  }

  .hero h1 { font-size: 32px; }

  .features-grid {
    grid-template-columns: 1fr 1fr;
  }

  .steps {
    grid-template-columns: 1fr;
  }

  .demo-summary {
    grid-template-columns: repeat(2, 1fr);
  }

  .nav-links a:not(.nav-btn-primary):not(.nav-btn-secondary) {
    display: none;
  }
}
</style>
