<template>
  <div>
    <!-- Compact trigger in sidebar -->
    <v-list-item
      :prepend-icon="running ? 'mdi-timer-stop' : 'mdi-timer-play-outline'"
      :title="running ? elapsed : 'Таймер'"
      rounded="xs"
      class="mb-1"
      :class="running ? 'timer-active' : ''"
      @click="running ? openStop() : openStart()"
    >
      <template v-if="running" #append>
        <v-icon size="8" color="error" class="blink">mdi-circle</v-icon>
      </template>
    </v-list-item>

    <!-- Start dialog -->
    <v-dialog v-model="startDialog" max-width="400">
      <v-card>
        <v-card-title>Начать учёт времени</v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <v-autocomplete
            v-model="selectedCase"
            :items="cases"
            item-title="title"
            item-value="id"
            label="Дело *"
            :rules="[v => !!v || 'Выберите дело']"
            :loading="loadingCases"
            class="mb-2"
          />
          <v-text-field v-model="taskDescription" label="Описание (необязательно)" class="mb-2" />
        </v-card-text>
        <v-divider />
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="startDialog = false">Отмена</v-btn>
          <v-btn color="primary" variant="tonal" :disabled="!selectedCase" @click="startTimer">
            <v-icon start>mdi-play</v-icon>Старт
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Stop dialog -->
    <v-dialog v-model="stopDialog" max-width="400">
      <v-card>
        <v-card-title class="d-flex align-center gap-2">
          <v-icon color="error" class="blink">mdi-circle</v-icon>
          Остановить таймер
        </v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <div class="text-h3 text-center font-weight-bold text-primary mb-2">{{ elapsed }}</div>
          <div class="text-center text-medium-emphasis text-caption mb-4">{{ startedCase }}</div>
          <v-textarea v-model="taskDescription" label="Описание работы" rows="2" auto-grow />
          <v-checkbox v-model="isBillable" label="Биллинговая запись" hide-details density="compact" class="mt-2" />
        </v-card-text>
        <v-divider />
        <v-card-actions>
          <v-btn variant="text" color="error" @click="discardTimer">Отменить</v-btn>
          <v-spacer />
          <v-btn variant="text" @click="stopDialog = false">Назад</v-btn>
          <v-btn color="success" variant="tonal" :loading="saving" @click="saveTimer">
            <v-icon start>mdi-check</v-icon>Сохранить
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useBillingStore } from '@/stores/billing'
import { useNotification } from '@/composables/useNotification'
import api from '@/plugins/axios'

const billingStore = useBillingStore()
const { success, error } = useNotification()

const startDialog = ref(false)
const stopDialog = ref(false)
const running = ref(false)
const saving = ref(false)

const selectedCase = ref(null)
const startedCase = ref('')
const taskDescription = ref('')
const isBillable = ref(true)
const startTime = ref(null)
const secondsElapsed = ref(0)

const cases = ref([])
const loadingCases = ref(false)

let ticker = null

const elapsed = computed(() => {
  const s = secondsElapsed.value
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
})

const elapsedHours = computed(() => Math.max(0.25, Math.round(secondsElapsed.value / 900) * 0.25))

async function loadCases() {
  if (cases.value.length) return
  loadingCases.value = true
  try {
    const { data } = await api.get('/api/v1/cases/', { params: { page_size: 200, status: 'active' } })
    cases.value = data.results || data
  } finally {
    loadingCases.value = false
  }
}

function openStart() {
  loadCases()
  startDialog.value = true
}

function openStop() {
  stopDialog.value = true
}

function startTimer() {
  if (!selectedCase.value) return
  const c = cases.value.find(c => c.id === selectedCase.value)
  startedCase.value = c?.title || ''
  startTime.value = new Date()
  secondsElapsed.value = 0
  running.value = true
  startDialog.value = false

  ticker = setInterval(() => { secondsElapsed.value++ }, 1000)

  // Persist across navigation
  localStorage.setItem('timer', JSON.stringify({
    caseId: selectedCase.value,
    caseTitle: startedCase.value,
    description: taskDescription.value,
    startTime: startTime.value.toISOString(),
  }))
}

async function saveTimer() {
  saving.value = true
  try {
    await billingStore.createTimeEntry({
      case: selectedCase.value,
      date: new Date().toISOString().slice(0, 10),
      hours: elapsedHours.value,
      description: taskDescription.value || `Работа по делу: ${startedCase.value}`,
      is_billable: isBillable.value,
    })
    success(`Записано ${elapsed.value} (${elapsedHours.value} ч.)`)
    resetTimer()
  } catch {
    error('Ошибка сохранения записи')
  } finally {
    saving.value = false
  }
}

function discardTimer() {
  resetTimer()
  stopDialog.value = false
}

function resetTimer() {
  clearInterval(ticker)
  ticker = null
  running.value = false
  secondsElapsed.value = 0
  selectedCase.value = null
  taskDescription.value = ''
  startedCase.value = ''
  stopDialog.value = false
  localStorage.removeItem('timer')
}

onMounted(() => {
  // Restore timer after page reload
  const saved = localStorage.getItem('timer')
  if (saved) {
    try {
      const t = JSON.parse(saved)
      selectedCase.value = t.caseId
      startedCase.value = t.caseTitle
      taskDescription.value = t.description || ''
      startTime.value = new Date(t.startTime)
      secondsElapsed.value = Math.floor((Date.now() - startTime.value.getTime()) / 1000)
      running.value = true
      ticker = setInterval(() => { secondsElapsed.value++ }, 1000)
    } catch {
      localStorage.removeItem('timer')
    }
  }
})

onUnmounted(() => clearInterval(ticker))
</script>

<style scoped>
.timer-active {
  background: rgba(var(--v-theme-primary), 0.08);
}
.blink {
  animation: blink 1.2s infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}
</style>
