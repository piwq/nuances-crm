<template>
  <div class="d-flex align-center justify-space-between mb-6">
    <div>
      <div class="text-h5 font-weight-bold">{{ title }}</div>
      <div v-if="subtitle" class="text-body-2 text-medium-emphasis mt-1">{{ subtitle }}</div>
    </div>
    <div class="d-flex gap-2">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: String,
  subtitle: String,
})
</script>
