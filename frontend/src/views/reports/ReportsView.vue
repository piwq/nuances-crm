<template>
  <div>
    <page-header title="Отчёты">
      <v-select
        v-model="months"
        :items="[{value:3,title:'3 месяца'},{value:6,title:'6 месяцев'},{value:12,title:'12 месяцев'}]"
        item-value="value"
        item-title="title"
        hide-details
        density="compact"
        style="width: 140px"
        @update:model-value="load"
      />
    </page-header>

    <div v-if="loading" class="d-flex justify-center pa-12">
      <v-progress-circular indeterminate color="primary" />
    </div>

    <template v-else>
      <!-- KPI Cards -->
      <v-row class="mb-6">
        <v-col cols="6" md="3">
          <v-card>
            <v-card-text>
              <div class="text-caption text-medium-emphasis">Всего дел</div>
              <div class="text-h4 font-weight-bold text-primary mt-1">{{ totalCases }}</div>
              <div class="text-caption mt-1">{{ activeCases }} активных</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="6" md="3">
          <v-card>
            <v-card-text>
              <div class="text-caption text-medium-emphasis">Выручка за период</div>
              <div class="text-h4 font-weight-bold text-success mt-1">{{ formatCurrency(totalRevenue) }}</div>
              <div class="text-caption mt-1">{{ formatHours(totalHours) }} часов</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="6" md="3">
          <v-card>
            <v-card-text>
              <div class="text-caption text-medium-emphasis">Оплачено счетов</div>
              <div class="text-h4 font-weight-bold text-success mt-1">{{ formatCurrency(paidAmount) }}</div>
              <div class="text-caption mt-1">{{ paidCount }} счетов</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="6" md="3">
          <v-card>
            <v-card-text>
              <div class="text-caption text-medium-emphasis">Просроченных счетов</div>
              <div class="text-h4 font-weight-bold text-error mt-1">{{ data?.overdue_invoices || 0 }}</div>
              <div class="text-caption mt-1">требуют внимания</div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-row class="mb-6">
        <!-- Revenue chart -->
        <v-col cols="12" md="8">
          <v-card>
            <v-card-title>Выручка по месяцам</v-card-title>
            <v-card-text style="height: 260px">
              <Bar v-if="revenueChartData" :data="revenueChartData" :options="barOptions" />
              <div v-else class="d-flex align-center justify-center h-100 text-medium-emphasis">Нет данных</div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Cases by status -->
        <v-col cols="12" md="4">
          <v-card>
            <v-card-title>Дела по статусам</v-card-title>
            <v-card-text style="height: 260px">
              <Doughnut v-if="statusChartData" :data="statusChartData" :options="doughnutOptions" />
              <div v-else class="d-flex align-center justify-center h-100 text-medium-emphasis">Нет данных</div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-row>
        <!-- Lawyers table -->
        <v-col cols="12" md="7">
          <v-card>
            <v-card-title>Статистика по юристам</v-card-title>
            <v-divider />
            <v-table density="compact">
              <thead>
                <tr>
                  <th>Юрист</th>
                  <th class="text-right">Часов</th>
                  <th class="text-right">Сумма</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(l, i) in data?.lawyers_stats" :key="i">
                  <td>{{ l.name || '—' }}</td>
                  <td class="text-right">{{ formatHours(l.total_hours) }}</td>
                  <td class="text-right font-weight-medium">{{ formatCurrency(l.total_amount) }}</td>
                </tr>
                <tr v-if="!data?.lawyers_stats?.length">
                  <td colspan="3" class="text-center text-medium-emphasis py-4">Нет данных</td>
                </tr>
              </tbody>
            </v-table>
          </v-card>
        </v-col>

        <!-- Invoices summary -->
        <v-col cols="12" md="5">
          <v-card>
            <v-card-title>Счета по статусам</v-card-title>
            <v-divider />
            <v-table density="compact">
              <thead>
                <tr>
                  <th>Статус</th>
                  <th class="text-right">Кол-во</th>
                  <th class="text-right">Сумма</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="s in INVOICE_STATUSES" :key="s.value">
                  <td><status-chip :value="s.value" :options="INVOICE_STATUSES" /></td>
                  <td class="text-right">{{ data?.invoices_summary?.[s.value]?.count || 0 }}</td>
                  <td class="text-right">{{ formatCurrency(data?.invoices_summary?.[s.value]?.total || 0) }}</td>
                </tr>
              </tbody>
            </v-table>
          </v-card>
        </v-col>
      </v-row>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Bar, Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement } from 'chart.js'
import { formatCurrency, formatHours } from '@/utils/formatters'
import { CASE_STATUSES, INVOICE_STATUSES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusChip from '@/components/common/StatusChip.vue'
import api from '@/plugins/axios'

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement)

const loading = ref(false)
const months = ref(6)
const data = ref(null)

const MONTH_NAMES = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек']
const STATUS_COLORS = {
  new: '#8fa7c4', active: '#5BA85A', on_hold: '#D9A84A',
  closed: '#9e9e9e', archived: '#c8c0b0',
}

const totalCases = computed(() => Object.values(data.value?.cases_by_status || {}).reduce((a, b) => a + b, 0))
const activeCases = computed(() => data.value?.cases_by_status?.active || 0)
const totalRevenue = computed(() => (data.value?.revenue_by_month || []).reduce((s, r) => s + r.total_amount, 0))
const totalHours = computed(() => (data.value?.revenue_by_month || []).reduce((s, r) => s + r.total_hours, 0))
const paidAmount = computed(() => data.value?.invoices_summary?.paid?.total || 0)
const paidCount = computed(() => data.value?.invoices_summary?.paid?.count || 0)

const revenueChartData = computed(() => {
  const rows = data.value?.revenue_by_month
  if (!rows?.length) return null
  return {
    labels: rows.map(r => {
      const [y, m] = r.month.split('-')
      return `${MONTH_NAMES[parseInt(m) - 1]} ${y}`
    }),
    datasets: [{
      label: 'Выручка (₽)',
      data: rows.map(r => r.total_amount),
      backgroundColor: '#2E5984',
      borderRadius: 4,
    }],
  }
})

const statusChartData = computed(() => {
  const s = data.value?.cases_by_status
  if (!s) return null
  const entries = Object.entries(s).filter(([, v]) => v > 0)
  if (!entries.length) return null
  return {
    labels: entries.map(([k]) => CASE_STATUSES.find(c => c.value === k)?.label || k),
    datasets: [{
      data: entries.map(([, v]) => v),
      backgroundColor: entries.map(([k]) => STATUS_COLORS[k] || '#9e9e9e'),
      borderWidth: 0,
    }],
  }
})

const barOptions = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: { y: { beginAtZero: true, ticks: { callback: v => `${(v/1000).toFixed(0)}к` } } },
}
const doughnutOptions = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { position: 'right', labels: { boxWidth: 12, font: { size: 11 } } } },
}

async function load() {
  loading.value = true
  try {
    const { data: d } = await api.get('/api/v1/billing/reports/', { params: { months: months.value } })
    data.value = d
  } catch {
    // silent
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
