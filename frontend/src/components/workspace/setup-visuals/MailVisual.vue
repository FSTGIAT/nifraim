<template>
  <div class="sv sv-mail" aria-hidden="true">
    <svg viewBox="0 0 440 330" fill="none">
      <!-- the agent's mailbox -->
      <rect x="70" y="92" width="170" height="120" rx="14" fill="#fff" stroke="#9FB9CC" stroke-width="2.5" />
      <path d="M72 100 l83 62 l83 -62" stroke="#2F6C94" stroke-width="3" stroke-linejoin="round" />
      <!-- a letter flies out to the insurer … -->
      <g class="svm-fly">
        <path d="M250 150 l70 -28 l-22 64 l-14 -22 z" fill="#4E9DD0" />
        <path d="M284 164 l36 -42" stroke="#fff" stroke-width="2" />
      </g>
      <!-- … the insurer's building -->
      <g>
        <rect x="318" y="176" width="70" height="70" rx="6" fill="#fff" stroke="#9FB9CC" stroke-width="2.5" />
        <path d="M312 178 l41 -24 l41 24 z" fill="#E8F1F8" stroke="#9FB9CC" stroke-width="2.5" stroke-linejoin="round" />
        <path d="M333 190 v42 M353 190 v42 M373 190 v42" stroke="#2F6C94" stroke-width="3" stroke-linecap="round" />
      </g>
      <!-- … and the reply comes back, tracked -->
      <g class="svm-reply">
        <rect x="110" y="232" width="92" height="56" rx="8" fill="#fff" stroke="#2F6C94" stroke-width="2.5" />
        <path d="M112 236 l45 30 l45 -30" stroke="#2F6C94" stroke-width="2.2" />
        <circle cx="206" cy="232" r="13" fill="#2E844A" />
        <path d="M200 232 l4 4 l8 -9" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />
      </g>
    </svg>
  </div>
</template>

<style scoped>
.sv { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
.sv svg { width: 100%; height: 100%; }
.svm-fly { animation: svmFly 5s ease-in-out infinite; }
@keyframes svmFly {
  0%, 10% { transform: translate(-30px, 10px); opacity: 0; }
  25%, 55% { transform: none; opacity: 1; }
  70%, 100% { transform: translate(40px, 30px); opacity: 0; }
}
.svm-reply { animation: svmReply 5s ease-in-out infinite; }
@keyframes svmReply {
  0%, 60% { transform: translateY(14px); opacity: 0; }
  75%, 95% { transform: none; opacity: 1; }
  100% { opacity: 0; }
}
@media (prefers-reduced-motion: reduce) { .svm-fly, .svm-reply { animation: none; opacity: 1; transform: none; } }
</style>
