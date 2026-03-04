<template>
  <div class="pricing-page">
    <!-- Nav -->
    <nav class="landing-nav">
      <div class="nav-content">
        <router-link to="/" class="nav-brand">
          <div class="nav-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <span class="nav-name">Nifraim</span>
        </router-link>
        <div class="nav-links">
          <router-link to="/login" class="nav-btn-secondary">התחברות</router-link>
          <router-link to="/signup" class="nav-btn-primary">התחל עכשיו</router-link>
        </div>
      </div>
    </nav>

    <div class="pricing-content">
      <div class="section-header">
        <h1>תמחור פשוט ושקוף</h1>
        <p>בחרו את המסלול המתאים לכם — ללא הפתעות</p>
      </div>

      <div class="plans">
        <div class="plan-card" :class="{ featured: false }">
          <div class="plan-name">חודשי</div>
          <div class="plan-price">
            <span class="price-amount ltr-number">295</span>
            <span class="price-currency">&#8362;</span>
            <span class="price-period">/ חודש</span>
          </div>
          <ul class="plan-features">
            <li v-for="f in planFeatures" :key="f">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              {{ f }}
            </li>
          </ul>
          <router-link to="/signup?plan=monthly" class="plan-btn">בחירת מסלול חודשי</router-link>
        </div>

        <div class="plan-card featured">
          <div class="plan-badge">חודש חינם!</div>
          <div class="plan-name">שנתי</div>
          <div class="plan-price">
            <span class="price-amount ltr-number">3,245</span>
            <span class="price-currency">&#8362;</span>
            <span class="price-period">/ שנה</span>
          </div>
          <div class="plan-savings">
            <span class="ltr-number">&#8362;295</span> חיסכון — חודש חינם!
          </div>
          <ul class="plan-features">
            <li v-for="f in planFeatures" :key="f">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              {{ f }}
            </li>
          </ul>
          <router-link to="/signup?plan=yearly" class="plan-btn primary">בחירת מסלול שנתי</router-link>
        </div>
      </div>

      <div class="faq">
        <h2>שאלות נפוצות</h2>
        <div class="faq-grid">
          <div class="faq-item" v-for="(q, i) in faq" :key="i">
            <h3>{{ q.question }}</h3>
            <p>{{ q.answer }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const planFeatures = [
  'העלאת קבצי פרודוקציה ללא הגבלה',
  'השוואת נפרעים מכל חברות הביטוח',
  'זיהוי אוטומטי של 7+ פורמטים',
  'ניהול טבלת עמלות',
  'שליחת בירורים במייל',
  'תמיכה טכנית מלאה',
]

const faq = [
  {
    question: 'האם יש תקופת ניסיון?',
    answer: 'כרגע אין תקופת ניסיון חינמית, אבל אנחנו מציעים הדגמה אישית למתעניינים.',
  },
  {
    question: 'אילו חברות ביטוח נתמכות?',
    answer: 'אקסלנס, הפניקס, מור, הכשרה, מנורה, אלטשולר — ותמיד מוסיפים חדשות.',
  },
  {
    question: 'איך מתבצע התשלום?',
    answer: 'תשלום מאובטח בכרטיס אשראי דרך Cardcom. בקרוב גם Bit ו-PayBox.',
  },
  {
    question: 'אפשר לבטל מנוי?',
    answer: 'כן, ניתן לבטל בכל עת. המנוי ימשיך עד סוף תקופת התשלום הנוכחית.',
  },
]
</script>

<style scoped>
.pricing-page {
  min-height: 100vh;
  background: var(--bg);
}

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
  text-decoration: none;
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
  gap: 12px;
}

.nav-btn-secondary {
  padding: 8px 20px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  font-weight: 600;
  color: var(--text);
  transition: all 0.2s;
}

.nav-btn-secondary:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.nav-btn-primary {
  padding: 8px 20px;
  border-radius: var(--radius-sm);
  background: var(--primary);
  color: white;
  font-weight: 600;
  transition: all 0.2s;
}

.nav-btn-primary:hover {
  background: var(--primary-deep);
}

.pricing-content {
  max-width: 900px;
  margin: 0 auto;
  padding: 120px 24px 80px;
}

.section-header {
  text-align: center;
  margin-bottom: 48px;
}

.section-header h1 {
  font-size: 40px;
  font-weight: 900;
  color: var(--text);
  margin-bottom: 12px;
}

.section-header p {
  font-size: 18px;
  color: var(--text-muted);
}

.plans {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 80px;
}

.plan-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  padding: 40px 32px;
  position: relative;
  transition: all 0.3s var(--transition);
}

.plan-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.plan-card.featured {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px var(--primary), var(--shadow-lg);
}

.plan-badge {
  position: absolute;
  top: -14px;
  right: 24px;
  padding: 4px 16px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-cyan) 100%);
  color: white;
  border-radius: 100px;
  font-size: 13px;
  font-weight: 700;
}

.plan-name {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 16px;
}

.plan-price {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 8px;
}

.price-amount {
  font-size: 48px;
  font-weight: 900;
  color: var(--text);
  line-height: 1;
}

.price-currency {
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
}

.price-period {
  font-size: 16px;
  color: var(--text-muted);
}

.plan-savings {
  display: inline-block;
  padding: 4px 12px;
  background: var(--green-light);
  color: var(--green);
  border-radius: 100px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 24px;
}

.plan-features {
  list-style: none;
  margin: 24px 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.plan-features li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--text-secondary);
}

.plan-btn {
  display: block;
  text-align: center;
  padding: 14px;
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 700;
  border: 1px solid var(--border);
  color: var(--text);
  transition: all 0.2s;
}

.plan-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.plan-btn.primary {
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-cyan) 100%);
  color: white;
  border: none;
}

.plan-btn.primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(1, 118, 211, 0.3);
}

/* FAQ */
.faq h2 {
  text-align: center;
  font-size: 28px;
  font-weight: 800;
  margin-bottom: 32px;
}

.faq-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.faq-item {
  padding: 24px;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}

.faq-item h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
}

.faq-item p {
  font-size: 14px;
  color: var(--text-muted);
  line-height: 1.6;
}

@media (max-width: 768px) {
  .plans {
    grid-template-columns: 1fr;
  }

  .faq-grid {
    grid-template-columns: 1fr;
  }
}
</style>
