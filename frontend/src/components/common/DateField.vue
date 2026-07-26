<template>
  <v-text-field
    :model-value="display"
    readonly
    prepend-inner-icon="mdi-calendar-outline"
    v-bind="$attrs"
    @click:clear="emit('update:modelValue', null)"
  >
    <v-menu v-model="menu" activator="parent" :close-on-content-click="false">
      <v-date-picker
        :model-value="dateObj"
        color="primary"
        show-adjacent-months
        @update:model-value="pick"
      />
    </v-menu>
  </v-text-field>
</template>

<script setup>
// Поле даты с гарантированным форматом дд.мм.гггг: нативный <input type="date">
// показывал порядок локали браузера (MM/DD/YYYY на английских браузерах).
// Наружу отдаёт ISO-строку YYYY-MM-DD — контракт с API не меняется.
import { ref, computed } from 'vue'
import { format, parseISO } from 'date-fns'

const props = defineProps({
  modelValue: { type: String, default: null },
})
const emit = defineEmits(['update:modelValue'])

const menu = ref(false)

const display = computed(() => {
  if (!props.modelValue) return ''
  try {
    return format(parseISO(props.modelValue), 'dd.MM.yyyy')
  } catch {
    return ''
  }
})

const dateObj = computed(() => (props.modelValue ? parseISO(props.modelValue) : null))

function pick(d) {
  const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  emit('update:modelValue', iso)
  menu.value = false
}
</script>
