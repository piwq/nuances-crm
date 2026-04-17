<template>
  <v-main class="bg-background d-flex align-center justify-center" style="min-height: 100vh;">
    <v-container style="max-width: 420px;">
      <div class="text-center mb-8">
        <img src="@/assets/logo.svg" alt="Нюансы" style="height: 44px;" />
        <div class="text-body-2 text-medium-emphasis mt-2">Система управления юридической фирмой</div>
      </div>
      <slot />
    </v-container>
  </v-main>
</template>
