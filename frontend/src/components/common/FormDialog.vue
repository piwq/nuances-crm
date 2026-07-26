<template>
  <v-dialog
    :model-value="modelValue"
    :max-width="maxWidth"
    persistent
    @update:model-value="v => emit('update:modelValue', v)"
    @click:outside="attempt"
    @after-leave="reset"
  >
    <div class="form-dialog-wrap" @keydown.esc="attempt">
      <slot />
      <v-fade-transition>
        <div v-if="attempts > 0" class="close-hint">
          Чтобы закрыть без сохранения — ещё {{ attemptsLeft }} {{ attemptsLeft === 1 ? 'раз' : 'раза' }} (Esc или клик мимо окна)
        </div>
      </v-fade-transition>
    </div>
  </v-dialog>
</template>

<script setup>
// Персистентный диалог формы: случайный Esc/клик мимо не стирает ввод
// (Vuetify подёргивает окно), но тройная попытка подряд закрывает его.
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  maxWidth: { type: [Number, String], default: 520 },
})
const emit = defineEmits(['update:modelValue'])

const attempts = ref(0)
let resetTimer = null

const attemptsLeft = computed(() => 3 - attempts.value)

function attempt() {
  clearTimeout(resetTimer)
  attempts.value += 1
  if (attempts.value >= 3) {
    emit('update:modelValue', false)
    reset()
    return
  }
  // пауза — значит передумал закрывать; счётчик и подсказка сбрасываются
  resetTimer = setTimeout(reset, 3000)
}

function reset() {
  clearTimeout(resetTimer)
  attempts.value = 0
}

watch(() => props.modelValue, (open) => { if (open) reset() })
</script>

<style scoped>
.form-dialog-wrap {
  position: relative;
}
.close-hint {
  position: absolute;
  top: calc(100% + 10px);
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
  background: rgba(14, 23, 41, 0.88);
  color: #fff;
  font-size: 0.75rem;
  padding: 6px 12px;
  border-radius: 16px;
  pointer-events: none;
}
</style>
