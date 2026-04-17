<template>
  <v-app>
    <router-view />
  </v-app>
</template>

<script setup>
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;700&display=swap');

:root {
  --v-theme-overlay-multiplier: 0.8;
}

body, .v-application {
  font-family: 'Outfit', sans-serif !important;
}

/* Modern Scrollbar */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(var(--v-theme-primary), 0.2);
  border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(var(--v-theme-primary), 0.4);
}

.glass-sidebar {
  background: rgba(var(--v-theme-surface), 0.7) !important;
  backdrop-filter: blur(20px) !important;
}

.text-gradient {
  background: linear-gradient(45deg, #6366F1, #EC4899);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.page-enter-active,
.page-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
