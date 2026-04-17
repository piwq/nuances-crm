<template>
  <v-main class="bg-background d-flex align-center justify-center" style="min-height: 100vh;">
    <v-container style="max-width: 440px;">
      <div class="text-center mb-6">
        <v-icon icon="mdi-scale-balance" color="primary" size="48" />
        <div class="text-h5 font-weight-bold mt-2 text-primary">Legal CRM</div>
        <div class="text-body-2 text-medium-emphasis">Система управления юридическим агентством</div>
      </div>
      <slot />
    </v-container>
  </v-main>
</template>
