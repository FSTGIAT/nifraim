<template>
  <div class="sv sv-portal" aria-hidden="true">
    <svg viewBox="0 0 440 330" fill="none">
      <!-- buildings backdrop -->
      <g opacity="0.5">
        <rect x="58" y="96" width="52" height="150" rx="6" fill="#F7E8D6"/>
        <rect x="70" y="112" width="10" height="10" rx="2" fill="#EAD0B4"/>
        <rect x="88" y="112" width="10" height="10" rx="2" fill="#EAD0B4"/>
        <rect x="70" y="132" width="10" height="10" rx="2" fill="#EAD0B4"/>
        <rect x="88" y="132" width="10" height="10" rx="2" fill="#EAD0B4"/>
        <rect x="70" y="152" width="10" height="10" rx="2" fill="#EAD0B4"/>
        <rect x="88" y="152" width="10" height="10" rx="2" fill="#EAD0B4"/>
        <rect x="330" y="120" width="46" height="126" rx="6" fill="#F7E8D6"/>
        <rect x="340" y="136" width="9" height="9" rx="2" fill="#EAD0B4"/>
        <rect x="356" y="136" width="9" height="9" rx="2" fill="#EAD0B4"/>
        <rect x="340" y="154" width="9" height="9" rx="2" fill="#EAD0B4"/>
        <rect x="356" y="154" width="9" height="9" rx="2" fill="#EAD0B4"/>
      </g>

      <!-- browser window -->
      <rect x="104" y="64" width="232" height="192" rx="14" fill="#fff" stroke="#EAD9C6" stroke-width="2.5"/>
      <rect x="104" y="64" width="232" height="34" rx="14" fill="#FDF1E3"/>
      <rect x="104" y="84" width="232" height="14" fill="#FDF1E3"/>
      <circle cx="318" cy="81" r="4" fill="#F57C00"/>
      <circle cx="304" cy="81" r="4" fill="#FFB74D"/>
      <circle cx="290" cy="81" r="4" fill="#F5C08A"/>
      <!-- url pill with lock -->
      <rect x="118" y="73" width="120" height="17" rx="8.5" fill="#fff" stroke="#F0DFC9" stroke-width="1.5"/>
      <g class="svl-urllock">
        <rect x="124" y="78" width="8" height="7" rx="1.6" fill="#2E844A"/>
        <path d="M125.6 78v-2a2.4 2.4 0 014.8 0v2" stroke="#2E844A" stroke-width="1.5" fill="none"/>
      </g>
      <rect x="140" y="79" width="66" height="5" rx="2.5" fill="#EFE2CE"/>

      <!-- login card -->
      <rect x="140" y="116" width="160" height="118" rx="12" fill="#FDF6ED" stroke="#F3E0C8" stroke-width="1.5"/>
      <!-- avatar -->
      <circle cx="220" cy="138" r="13" fill="#FFE2C4"/>
      <circle cx="220" cy="134" r="5" fill="#F57C00"/>
      <path d="M211 146c2-5 6-7 9-7s7 2 9 7" stroke="#F57C00" stroke-width="2.4" stroke-linecap="round" fill="none"/>
      <!-- fields that "type" -->
      <rect x="156" y="160" width="128" height="18" rx="8" fill="#fff" stroke="#F0DFC9" stroke-width="1.5"/>
      <rect class="svl-type svl-type-1" x="164" y="166" width="70" height="6" rx="3" fill="#F5A957"/>
      <rect x="156" y="186" width="128" height="18" rx="8" fill="#fff" stroke="#F0DFC9" stroke-width="1.5"/>
      <g class="svl-type svl-type-2">
        <circle cx="168" cy="195" r="2.6" fill="#E65100"/>
        <circle cx="178" cy="195" r="2.6" fill="#E65100"/>
        <circle cx="188" cy="195" r="2.6" fill="#E65100"/>
        <circle cx="198" cy="195" r="2.6" fill="#E65100"/>
        <circle cx="208" cy="195" r="2.6" fill="#E65100"/>
      </g>
      <!-- submit -->
      <rect class="svl-btn" x="156" y="212" width="128" height="16" rx="8" fill="#F57C00"/>

      <!-- key -->
      <g class="svl-key">
        <circle cx="94" cy="272" r="14" stroke="#E65100" stroke-width="4"/>
        <path d="M106 272h44M134 272v10M146 272v7" stroke="#E65100" stroke-width="4" stroke-linecap="round"/>
      </g>

      <!-- big lock that snaps closed -->
      <g class="svl-lock">
        <rect x="300" y="266" width="44" height="34" rx="9" fill="#F57C00"/>
        <path class="svl-shackle" d="M310 266v-10a12 12 0 0124 0v10" stroke="#E65100" stroke-width="5" fill="none" stroke-linecap="round"/>
        <circle cx="322" cy="281" r="4.5" fill="#fff"/>
        <rect x="320" y="283" width="4" height="8" rx="2" fill="#fff"/>
      </g>
    </svg>
  </div>
</template>

<script setup>
</script>

<style scoped>
.sv { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
.sv svg { width: 100%; height: 100%; }

.svl-type { transform-origin: right center; animation: svl-type 5.8s ease infinite; }
.svl-type-2 { animation-delay: 0.7s; }
@keyframes svl-type {
  0%, 8% { opacity: 0; transform: scaleX(0.1); }
  30%, 92% { opacity: 1; transform: scaleX(1); }
  100% { opacity: 0; }
}

.svl-btn { animation: svl-btn 5.8s ease infinite; transform-origin: 220px 220px; }
@keyframes svl-btn {
  0%, 38% { opacity: 0.45; transform: scale(0.97); }
  48%, 60% { opacity: 1; transform: scale(1.04); }
  70%, 100% { opacity: 1; transform: scale(1); }
}

.svl-key { animation: svl-key 5.8s ease-in-out infinite; transform-origin: 94px 272px; }
@keyframes svl-key {
  0%, 100% { transform: rotate(-8deg); }
  50% { transform: rotate(8deg); }
}

.svl-shackle { transform-origin: 322px 266px; animation: svl-shackle 5.8s ease infinite; }
@keyframes svl-shackle {
  0%, 44% { transform: translateY(-7px); }
  56%, 100% { transform: translateY(0); }
}
.svl-lock { animation: svl-lockpop 5.8s ease infinite; transform-origin: 322px 283px; }
@keyframes svl-lockpop {
  0%, 52% { transform: scale(1); }
  58% { transform: scale(1.1); }
  64%, 100% { transform: scale(1); }
}

@media (prefers-reduced-motion: reduce) {
  .svl-type, .svl-btn, .svl-key, .svl-shackle, .svl-lock { animation: none; }
  .svl-type { opacity: 1; }
}
</style>
