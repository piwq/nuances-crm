<template>
  <v-dialog
    :model-value="modelValue"
    :max-width="maxWidth"
    :fullscreen="display.xs.value"
    persistent
    @update:model-value="v => emit('update:modelValue', v)"
    @click:outside="attempt"
    @after-leave="reset"
  >
    <div class="form-dialog-wrap" @input="markDirty" @change="markDirty">
      <slot />
      <v-fade-transition>
        <div v-if="attempts > 0" class="close-hint">
          Есть несохранённый ввод — чтобы закрыть, ещё {{ attemptsLeft }} {{ attemptsLeft === 1 ? 'раз' : 'раза' }} (Esc или клик мимо окна)
        </div>
      </v-fade-transition>
    </div>
  </v-dialog>
</template>

<script setup>
// Диалог формы: пустой закрывается с первого Esc/клика мимо, как обычный.
// Как только внутри что-то ввели — включается защита: Vuetify подёргивает
// окно, а тройная попытка подряд закрывает его (подсказка после первой).
import { ref, computed, watch, onUnmounted } from 'vue'
import { useDisplay } from 'vuetify'

const props = defineProps({
  modelValue: Boolean,
  maxWidth: { type: [Number, String], default: 520 },
})
const emit = defineEmits(['update:modelValue'])

const display = useDisplay()

const attempts = ref(0)
const dirty = ref(false)
let resetTimer = null

const attemptsLeft = computed(() => 3 - attempts.value)

function markDirty() {
  dirty.value = true
}

function close() {
  emit('update:modelValue', false)
  reset()
}

function attempt() {
  if (!dirty.value) {
    close()
    return
  }
  clearTimeout(resetTimer)
  attempts.value += 1
  if (attempts.value >= 3) {
    close()
    return
  }
  // пауза — значит передумал закрывать; счётчик и подсказка сбрасываются
  resetTimer = setTimeout(reset, 3000)
}

function reset() {
  clearTimeout(resetTimer)
  attempts.value = 0
}

// Esc ловим на window: фокус в открытом диалоге сидит на контейнере
// оверлея Vuetify, через слот событие клавиатуры не проходит
function onKeydown(e) {
  if (e.key === 'Escape') attempt()
}

watch(() => props.modelValue, (open) => {
  reset()
  dirty.value = false
  if (open) window.addEventListener('keydown', onKeydown)
  else window.removeEventListener('keydown', onKeydown)
})

onUnmounted(() => window.removeEventListener('keydown', onKeydown))
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
