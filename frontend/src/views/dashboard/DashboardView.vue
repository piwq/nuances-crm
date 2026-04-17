<template>
  <div>
    <page-header title="Дашборд" :subtitle="`Добро пожаловать, ${auth.user?.first_name || auth.user?.username}`" />

    <!-- Stats Cards -->
    <v-row class="mb-6">
      <v-col v-for="stat in stats" :key="stat.title" cols="12" sm="6" lg="3">
        <v-card>
          <v-card-text class="d-flex align-center justify-space-between">
            <div>
              <div class="text-body-2 text-medium-emphasis">{{ stat.title }}</div>
              <div class="text-h4 font-weight-bold mt-1" :class="`text-${stat.color}`">
                {{ stat.loading ? '...' : stat.value }}
              </div>
            </div>
            <v-icon :icon="stat.icon" :color="stat.color" size="40" />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row>
      <!-- Upcoming Events -->
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title class="d-flex align-center gap-2">
            <v-icon icon="mdi-calendar" color="primary" />
            Ближайшие события
          </v-card-title>
          <v-card-text class="pa-0">
            <v-list v-if="upcomingEvents.length">
              <v-list-item
                v-for="event in upcomingEvents"
                :key="event.id"
                :subtitle="formatDateTime(event.start_datetime)"
              >
                <template #prepend>
                  <v-icon :color="eventColor(event.event_type)" icon="mdi-circle" size="10" class="mr-3" />
                </template>
                <template #title>
                  <span class="text-body-2 font-weight-medium">{{ event.title }}</span>
                </template>
                <template #append>
                  <v-chip size="x-small" :color="eventColor(event.event_type)" variant="tonal">
                    {{ eventLabel(event.event_type) }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
            <div v-else class="pa-4 text-medium-emphasis text-center">Нет предстоящих событий</div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Overdue Tasks -->
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title class="d-flex align-center gap-2">
            <v-icon icon="mdi-alert-circle" color="error" />
            Просроченные задачи
          </v-card-title>
          <v-card-text class="pa-0">
            <v-list v-if="overdueTasks.length">
              <v-list-item
                v-for="task in overdueTasks.slice(0, 8)"
                :key="task.id"
                :subtitle="task.case_title || 'Без дела'"
                :to="`/tasks`"
              >
                <template #title>
                  <span class="text-body-2 font-weight-medium">{{ task.title }}</span>
                </template>
                <template #append>
                  <v-chip size="x-small" color="error" variant="tonal">
                    {{ formatDate(task.due_date) }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
            <div v-else class="pa-4 text-medium-emphasis text-center text-success">
              <v-icon icon="mdi-check-circle" class="mr-1" />
              Нет просроченных задач
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useCasesStore } from '@/stores/cases'
import { useTasksStore } from '@/stores/tasks'
import { useEventsStore } from '@/stores/events'
import { useAuthStore } from '@/stores/auth'
import { useBillingStore } from '@/stores/billing'
import { formatDate, formatDateTime } from '@/utils/formatters'
import { EVENT_TYPES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import { format, startOfToday, addDays } from 'date-fns'

const auth = useAuthStore()
const casesStore = useCasesStore()
const tasksStore = useTasksStore()
const eventsStore = useEventsStore()
const billingStore = useBillingStore()

const caseStats = ref(null)
const statsLoading = ref(true)

const stats = computed(() => [
  {
    title: 'Активных дел',
    value: caseStats.value?.by_status?.active || 0,
    icon: 'mdi-briefcase',
    color: 'primary',
    loading: statsLoading.value,
  },
  {
    title: 'Задач в работе',
    value: tasksStore.tasks.filter(t => t.status === 'in_progress').length,
    icon: 'mdi-checkbox-marked-circle',
    color: 'info',
    loading: statsLoading.value,
  },
  {
    title: 'Просроченных задач',
    value: tasksStore.overdueTasks.length,
    icon: 'mdi-alert-circle',
    color: 'error',
    loading: statsLoading.value,
  },
  {
    title: 'Новых дел',
    value: caseStats.value?.by_status?.new || 0,
    icon: 'mdi-star',
    color: 'warning',
    loading: statsLoading.value,
  },
])

const upcomingEvents = computed(() =>
  eventsStore.events
    .filter(e => new Date(e.start_datetime) >= new Date())
    .sort((a, b) => new Date(a.start_datetime) - new Date(b.start_datetime))
    .slice(0, 8)
)

const overdueTasks = computed(() => tasksStore.overdueTasks)

function eventColor(type) {
  return EVENT_TYPES.find(t => t.value === type)?.color || 'grey'
}

function eventLabel(type) {
  return EVENT_TYPES.find(t => t.value === type)?.label || type
}

onMounted(async () => {
  statsLoading.value = true
  const today = format(startOfToday(), "yyyy-MM-dd'T'HH:mm:ss")
  const future = format(addDays(new Date(), 30), "yyyy-MM-dd'T'HH:mm:ss")
  await Promise.all([
    casesStore.fetchStats().then(d => caseStats.value = d),
    tasksStore.fetchTasks({ page_size: 50, status: 'todo,in_progress' }),
    eventsStore.fetchEvents(today, future),
  ])
  statsLoading.value = false
})
</script>
