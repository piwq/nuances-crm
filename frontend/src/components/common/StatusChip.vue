<template>
  <span :class="['status-chip', chipClass]">
    <span class="status-dot" />
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: String,
  options: { type: Array, default: () => [] },
})

const found = computed(() => props.options.find(o => o.value === props.value))
const label = computed(() => found.value?.label || props.value || '—')

const chipClass = computed(() => {
  const color = found.value?.color || props.value
  const map = {
    primary: 'chip-new',
    info:    'chip-new',
    success: 'chip-active',
    warning: 'chip-hold',
    error:   'chip-overdue',
    secondary: 'chip-urgent',
    grey:    'chip-closed',
    // explicit value keys
    new:      'chip-new',
    active:   'chip-active',
    on_hold:  'chip-hold',
    closed:   'chip-closed',
    archived: 'chip-closed',
    overdue:  'chip-overdue',
    paid:     'chip-paid',
    sent:     'chip-sent',
    draft:    'chip-draft',
    cancelled:'chip-closed',
    low:      'chip-closed',
    medium:   'chip-new',
    high:     'chip-hold',
    urgent:   'chip-urgent',
    todo:     'chip-new',
    in_progress: 'chip-active',
    done:     'chip-paid',
  }
  return map[color] || map[props.value] || 'chip-closed'
})
</script>

<style scoped>
.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 3px;
  white-space: nowrap;
}
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}
.chip-new      { background: #EEF1F5; color: #2E3C56; }
.chip-active   { background: #DDE8DF; color: #3F6B4C; }
.chip-hold     { background: #F5E9CF; color: #A8823B; }
.chip-closed   { background: #F5F3EC; color: #7D7665; }
.chip-overdue  { background: #F1DAD0; color: #8A3A1E; }
.chip-urgent   { background: #F3DDE0; color: #7A1E2B; }
.chip-paid     { background: #DDE8DF; color: #3F6B4C; }
.chip-sent     { background: #EEF1F5; color: #2E3C56; }
.chip-draft    { background: #F5F3EC; color: #7D7665; }
</style>
