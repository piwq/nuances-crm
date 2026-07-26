<template>
  <div>
    <page-header title="Дела — Канбан">
      <v-btn variant="tonal" prepend-icon="mdi-format-list-bulleted" to="/cases">Список</v-btn>
    </page-header>

    <div v-if="loading" class="d-flex justify-center pa-12">
      <v-progress-circular indeterminate color="primary" />
    </div>

    <div v-else class="kanban-board">
      <div
        v-for="col in columns"
        :key="col.status"
        class="kanban-col"
        @dragover.prevent
        @drop="onDrop($event, col.status)"
      >
        <div class="kanban-col-header" :style="`border-color: ${col.color}`">
          <span class="font-weight-semibold">{{ col.label }}</span>
          <v-chip size="x-small" variant="tonal" class="ml-2">{{ grouped[col.status]?.length || 0 }}</v-chip>
        </div>

        <div class="kanban-cards">
          <div
            v-for="c in grouped[col.status] || []"
            :key="c.id"
            class="kanban-card"
            draggable="true"
            @dragstart="onDragStart($event, c)"
          >
            <router-link :to="`/cases/${c.uuid}`" class="text-body-2 font-weight-medium text-primary text-decoration-none d-block mb-1">
              {{ c.title }}
            </router-link>
            <div class="text-caption text-medium-emphasis mb-1">{{ c.case_number }}</div>
            <div class="text-caption text-medium-emphasis">{{ c.client_name }}</div>
            <div class="d-flex align-center mt-2 gap-1">
              <v-chip v-if="c.open_tasks_count" size="x-small" color="warning" variant="tonal">
                <v-icon start size="10">mdi-checkbox-marked-circle-outline</v-icon>{{ c.open_tasks_count }}
              </v-chip>
              <v-chip v-if="c.lead_lawyer_name" size="x-small" variant="outlined">{{ c.lead_lawyer_name }}</v-chip>
            </div>
          </div>
          <div v-if="!grouped[col.status]?.length" class="kanban-empty text-caption text-medium-emphasis">
            Нет дел
          </div>
        </div>
      </div>
    </div>

    <v-snackbar v-model="moving" color="primary" timeout="-1" location="bottom right">
      <v-progress-circular indeterminate size="16" class="mr-2" />
      Перемещение...
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useCasesStore } from '@/stores/cases'
import { CASE_STATUSES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import api from '@/plugins/axios'

const store = useCasesStore()
const loading = ref(false)
const moving = ref(false)
const cases = ref([])
let draggedCase = null

const STATUS_COLORS = {
  new: '#8fa7c4', active: '#5BA85A', on_hold: '#D9A84A',
  closed: '#ef5350', archived: '#9e9e9e',
}

const columns = CASE_STATUSES.map(s => ({ ...s, color: STATUS_COLORS[s.value] || '#9e9e9e' }))

const grouped = computed(() => {
  const g = {}
  for (const s of CASE_STATUSES) g[s.value] = []
  for (const c of cases.value) {
    if (g[c.status]) g[c.status].push(c)
  }
  return g
})

function onDragStart(event, c) {
  draggedCase = c
  event.dataTransfer.effectAllowed = 'move'
}

async function onDrop(event, newStatus) {
  if (!draggedCase || draggedCase.status === newStatus) return
  const prev = draggedCase.status
  draggedCase.status = newStatus
  moving.value = true
  try {
    await store.changeStatus(draggedCase.uuid, newStatus)
  } catch {
    draggedCase.status = prev
  } finally {
    moving.value = false
    draggedCase = null
  }
}

async function load() {
  loading.value = true
  try {
    let page = 1
    let all = []
    while (true) {
      const { data } = await api.get('/api/v1/cases/', { params: { page, page_size: 100 } })
      all = all.concat(data.results || data)
      if (!data.next) break
      page++
    }
    cases.value = all
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.kanban-board {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  align-items: flex-start;
  padding-bottom: 16px;
}

.kanban-col {
  flex: 0 0 240px;
  background: rgba(var(--v-theme-surface-variant), 0.4);
  border-radius: 8px;
  padding: 8px;
  min-height: 200px;
}

.kanban-col-header {
  border-left: 3px solid;
  padding: 6px 8px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
}

.kanban-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.kanban-card {
  background: rgb(var(--v-theme-surface));
  border-radius: 6px;
  padding: 10px 12px;
  cursor: grab;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  transition: box-shadow 0.15s;
}

.kanban-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.12);
}

.kanban-card:active {
  cursor: grabbing;
}

.kanban-empty {
  padding: 12px 8px;
  text-align: center;
}
</style>
