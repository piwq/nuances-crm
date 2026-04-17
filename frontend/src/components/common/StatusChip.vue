<template>
  <v-chip
    :color="color"
    size="small"
    label
    variant="tonal"
  >
    {{ label }}
  </v-chip>
</template>

<script setup>
const props = defineProps({
  value: String,
  options: {
    type: Array,
    default: () => [],
  },
})

import { computed } from 'vue'
const found = computed(() => props.options.find(o => o.value === props.value))
const color = computed(() => found.value?.color || 'grey')
const label = computed(() => found.value?.label || props.value || '—')
</script>
