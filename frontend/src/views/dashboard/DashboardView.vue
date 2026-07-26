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

    <!-- Charts -->
    <v-row class="mb-6">
      <v-col cols="12" md="5">
        <v-card>
          <v-card-title class="d-flex align-center gap-2">
            <v-icon icon="mdi-chart-donut" color="primary" />
            Дела по категориям
          </v-card-title>
          <v-card-text class="d-flex justify-center" style="height: 240px">
            <Doughnut v-if="categoryChartData" :data="categoryChartData" :options="doughnutOptions" />
            <div v-else class="d-flex align-center text-medium-emphasis">Нет данных</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="7">
        <v-card>
          <v-card-title class="d-flex align-center gap-2">
            <v-icon icon="mdi-chart-bar" color="primary" />
            Биллинг по месяцам
          </v-card-title>
          <v-card-text style="height: 240px">
            <Bar v-if="billingChartData" :data="billingChartData" :options="barOptions" />
            <div v-else class="d-flex align-center justify-center text-medium-emphasis" style="height:100%">Нет данных</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mb-6">
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

    <v-row>
      <!-- Upcoming Deadlines (7 days) -->
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title class="d-flex align-center gap-2">
            <v-icon icon="mdi-clock-alert" color="warning" />
            Дедлайны — следующие 7 дней
          </v-card-title>
          <v-card-text class="pa-0">
            <div v-if="deadlinesLoading" class="d-flex justify-center pa-4">
              <v-progress-circular indeterminate color="primary" size="24" />
            </div>
            <v-list v-else-if="upcomingDeadlines.length">
              <v-list-item
                v-for="task in upcomingDeadlines"
                :key="task.id"
                :subtitle="task.case_title || 'Без дела'"
                :to="`/tasks`"
              >
                <template #title>
                  <span class="text-body-2 font-weight-medium">{{ task.title }}</span>
                </template>
                <template #append>
                  <v-chip
                    size="x-small"
                    :color="daysUntil(task.due_date) <= 1 ? 'error' : 'warning'"
                    variant="tonal"
                  >
                    {{ daysUntil(task.due_date) === 0 ? 'Сегодня' : daysUntil(task.due_date) === 1 ? 'Завтра' : `${daysUntil(task.due_date)}д` }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
            <div v-else class="pa-4 text-medium-emphasis text-center">
              <v-icon icon="mdi-check-all" class="mr-1" />
              Нет дедлайнов на 7 дней
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Activity Feed -->
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title class="d-flex align-center gap-2">
            <v-icon icon="mdi-history" color="primary" />
            Лента активности
          </v-card-title>
          <v-card-text class="pa-0">
            <div v-if="activityLoading" class="d-flex justify-center pa-4">
              <v-progress-circular indeterminate color="primary" size="24" />
            </div>
            <v-list v-else-if="activityFeed.length" density="compact" class="py-0">
              <v-list-item
                v-for="entry in activityFeed"
                :key="entry.id"
                :subtitle="entry.user_name + ' · ' + formatTimeAgo(entry.timestamp)"
              >
                <template #prepend>
                  <v-icon :color="activityColor(entry.action)" size="16" class="mr-2">
                    {{ activityIcon(entry.action) }}
                  </v-icon>
                </template>
                <template #title>
                  <span class="text-body-2">{{ entry.description }}</span>
                </template>
              </v-list-item>
            </v-list>
            <div v-else class="pa-4 text-medium-emphasis text-center">Нет активности</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { Doughnut, Bar } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title } from 'chart.js'
import { useCasesStore } from '@/stores/cases'
import { useTasksStore } from '@/stores/tasks'
import { useEventsStore } from '@/stores/events'
import { useAuthStore } from '@/stores/auth'
import { formatDate, formatDateTime } from '@/utils/formatters'
import { EVENT_TYPES, CASE_CATEGORIES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import { format, startOfToday, addDays, differenceInCalendarDays, parseISO, formatDistanceToNow } from 'date-fns'
import { ru } from 'date-fns/locale'
import api from '@/plugins/axios'

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title)

const auth = useAuthStore()
const casesStore = useCasesStore()
const tasksStore = useTasksStore()
const eventsStore = useEventsStore()

const caseStats = ref(null)
const monthlyBilling = ref([])
const statsLoading = ref(true)
const upcomingDeadlines = ref([])
const deadlinesLoading = ref(false)
const activityFeed = ref([])
const activityLoading = ref(false)

const CHART_COLORS = ['#2E5984', '#4A90D9', '#5BA85A', '#D9A84A', '#C95C3B', '#8B6FAE', '#5BA8A8', '#D96B84']

const categoryChartData = computed(() => {
  if (!caseStats.value?.by_category) return null
  const cats = Object.entries(caseStats.value.by_category).filter(([, v]) => v > 0)
  if (!cats.length) return null
  return {
    labels: cats.map(([k]) => CASE_CATEGORIES.find(c => c.value === k)?.label || k),
    datasets: [{
      data: cats.map(([, v]) => v),
      backgroundColor: CHART_COLORS.slice(0, cats.length),
      borderWidth: 0,
    }],
  }
})

const billingChartData = computed(() => {
  if (!monthlyBilling.value.length) return null
  const MONTH_NAMES = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
  return {
    labels: monthlyBilling.value.map(r => {
      const [y, m] = r.month.split('-')
      return `${MONTH_NAMES[parseInt(m) - 1]} ${y}`
    }),
    datasets: [{
      label: 'Сумма (₽)',
      data: monthlyBilling.value.map(r => r.total_amount),
      backgroundColor: '#2E5984',
      borderRadius: 4,
    }],
  }
})

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { position: 'right', labels: { boxWidth: 12, font: { size: 11 } } } },
}

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: { y: { beginAtZero: true, ticks: { callback: v => `${(v/1000).toFixed(0)}к` } } },
}

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

function daysUntil(dateStr) {
  return Math.max(0, differenceInCalendarDays(parseISO(dateStr), startOfToday()))
}
function formatTimeAgo(dateStr) {
  try { return formatDistanceToNow(parseISO(dateStr), { addSuffix: true, locale: ru }) } catch { return '' }
}

const ACTION_ICONS = { CREATE: 'mdi-plus-circle', UPDATE: 'mdi-pencil', DELETE: 'mdi-delete', STATUS_CHANGE: 'mdi-swap-horizontal', DOWNLOAD: 'mdi-download', UPLOAD: 'mdi-upload' }
const ACTION_COLORS = { CREATE: 'success', UPDATE: 'primary', DELETE: 'error', STATUS_CHANGE: 'warning', DOWNLOAD: 'grey', UPLOAD: 'teal' }
function activityIcon(action) { return ACTION_ICONS[action] || 'mdi-information' }
function activityColor(action) { return ACTION_COLORS[action] || 'grey' }

async function loadDeadlines() {
  deadlinesLoading.value = true
  try {
    const today = format(startOfToday(), 'yyyy-MM-dd')
    const in7 = format(addDays(new Date(), 7), 'yyyy-MM-dd')
    const { data } = await api.get('/api/v1/tasks/', {
      params: { due_date_after: today, due_date_before: in7, page_size: 20 },
    })
    upcomingDeadlines.value = (data.results || data).filter(t => !['done', 'cancelled'].includes(t.status))
  } finally {
    deadlinesLoading.value = false
  }
}

async function loadActivity() {
  activityLoading.value = true
  try {
    const { data } = await api.get('/api/v1/activity/')
    activityFeed.value = data.results || data
  } catch {
    // non-critical
  } finally {
    activityLoading.value = false
  }
}

onMounted(async () => {
  statsLoading.value = true
  const today = format(startOfToday(), "yyyy-MM-dd'T'HH:mm:ss")
  const future = format(addDays(new Date(), 30), "yyyy-MM-dd'T'HH:mm:ss")
  try {
    // allSettled: отказ одного запроса не должен вешать весь дашборд
    await Promise.allSettled([
      casesStore.fetchStats().then(d => caseStats.value = d),
      tasksStore.fetchTasks({ page_size: 50, status: 'todo,in_progress' }),
      eventsStore.fetchEvents(today, future),
      api.get('/api/v1/billing/monthly-stats/').then(r => monthlyBilling.value = r.data),
      loadDeadlines(),
      loadActivity(),
    ])
  } finally {
    statsLoading.value = false
  }
})
</script>
