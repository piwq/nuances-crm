<template>
  <v-app>
    <router-view />
  </v-app>
</template>

<script setup>
</script>

<style>
/* Design tokens */
:root {
  --ink-50:  #EEF1F5;
  --ink-100: #D6DCE6;
  --ink-200: #AAB5C7;
  --ink-300: #7585A0;
  --ink-400: #4B5B77;
  --ink-500: #2E3C56;
  --ink-600: #223049;
  --ink-700: #17223A;
  --ink-800: #0E1729;
  --ink-900: #070D1B;

  --parchment-50:  #FBFAF6;
  --parchment-100: #F5F3EC;
  --parchment-200: #EAE6DA;
  --parchment-300: #D7D2C2;
  --parchment-400: #A9A292;
  --parchment-500: #7D7665;

  --claret-100: #F3DDE0;
  --claret-500: #7A1E2B;
  --claret-600: #5F1520;
  --gilt-100:   #F5E9CF;
  --gilt-500:   #A8823B;
  --moss-100:   #DDE8DF;
  --moss-500:   #3F6B4C;
  --rust-100:   #F1DAD0;
  --rust-500:   #8A3A1E;

  --font-serif: 'Source Serif 4', Georgia, serif;
  --font-sans:  'Inter', -apple-system, sans-serif;
  --font-mono:  'JetBrains Mono', monospace;

  --radius-xs: 2px;
  --radius-sm: 4px;
  --radius-md: 6px;

  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --dur-fast: 120ms;
  --dur-med:  200ms;
}

body, .v-application {
  font-family: var(--font-sans) !important;
  -webkit-font-smoothing: antialiased;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--parchment-300); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--parchment-400); }

.font-serif { font-family: var(--font-serif) !important; }
.font-mono  { font-family: var(--font-mono) !important; }
.case-number { font-family: var(--font-mono) !important; font-size: 0.8125rem; color: var(--ink-400); }

.page-enter-active,
.page-leave-active {
  transition: opacity var(--dur-med) var(--ease-out), transform var(--dur-med) var(--ease-out);
}
.page-enter-from { opacity: 0; transform: translateY(6px); }
.page-leave-to   { opacity: 0; transform: translateY(-4px); }
</style>
