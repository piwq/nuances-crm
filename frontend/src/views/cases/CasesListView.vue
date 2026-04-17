<template>
  <div>
    <page-header title="Дела" :subtitle="`Всего: ${store.pagination.total}`">
      <v-btn color="primary" prepend-icon="mdi-plus" to="/cases/new">Новое дело</v-btn>
    </page-header>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row dense>
          <v-col cols="12" md="4">
            <v-text-field v-model="search" label="Поиск..." prepend-inner-icon="mdi-magnify" clearable hide-details @update:model-value="debouncedFetch" />
          </v-col>
          <v-col cols="6" md="2">
            <v-select v-model="filters.status" :items="statusOptions" item-value="value" item-title="title" label="Статус" clearable hide-details @update:model-value="fetchData" />
          </v-col>
          <v-col cols="6" md="2">
            <v-select v-model="filters.category" :items="categoryOptions" item-value="value" item-title="title" label="Категория" clearable hide-details @update:model-value="fetchData" />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <v-card>
      <v-data-table-server
        :headers="headers"
        :items="store.cases"
        :items-length="store.pagination.total"
        :loading="store.loading"
        :items-per-page="25"
        @update:options="onTableUpdate"
      >
        <template #item.title="{ item }">
          <router-link :to="`/cases/${item.id}`" class="text-primary font-weight-medium text-decoration-none">
            {{ item.title }}
          </router-link>
          <div class="text-caption text-medium-emphasis">{{ item.case_number }}</div>
        </template>
        <template #item.status="{ item }">
          <status-chip :value="item.status" :options="CASE_STATUSES" />
        </template>
        <template #item.category="{ item }">
          {{ CASE_CATEGORIES.find(c => c.value === item.category)?.label || item.category }}
        </template>
        <template #item.opened_at="{ item }">
          {{ formatDate(item.opened_at) }}
        </template>
        <template #item.open_tasks_count="{ item }">
          <v-chip size="x-small" :color="item.open_tasks_count > 0 ? 'warning' : 'grey'" variant="tonal">
            {{ item.open_tasks_count }}
          </v-chip>
        </template>
      </v-data-table-server>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useCasesStore } from '@/stores/cases'
import { formatDate } from '@/utils/formatters'
import { CASE_STATUSES, CASE_CATEGORIES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusChip from '@/components/common/StatusChip.vue'

const store = useCasesStore()
const search = ref('')
const filters = ref({ status: '', category: '' })
let currentOptions = { page: 1, itemsPerPage: 25, sortBy: [] }
let searchTimeout = null

const statusOptions = [{ value: '', title: 'Все' }, ...CASE_STATUSES.map(s => ({ value: s.value, title: s.label }))]
const categoryOptions = [{ value: '', title: 'Все' }, ...CASE_CATEGORIES.map(c => ({ value: c.value, title: c.label }))]

const headers = [
  { title: 'Дело', key: 'title', sortable: true },
  { title: 'Клиент', key: 'client_name', sortable: false },
  { title: 'Статус', key: 'status', sortable: false },
  { title: 'Категория', key: 'category', sortable: false },
  { title: 'Юрист', key: 'lead_lawyer_name', sortable: false },
  { title: 'Открыто', key: 'opened_at', sortable: true },
  { title: 'Задач', key: 'open_tasks_count', sortable: false },
]

function buildParams() {
  const params = { page: currentOptions.page, page_size: currentOptions.itemsPerPage }
  if (search.value) params.search = search.value
  if (filters.value.status) params.status = filters.value.status
  if (filters.value.category) params.category = filters.value.category
  if (currentOptions.sortBy?.length) {
    const s = currentOptions.sortBy[0]
    params.ordering = s.order === 'desc' ? `-${s.key}` : s.key
  }
  return params
}

function fetchData() { store.fetchCases(buildParams()) }
function debouncedFetch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(fetchData, 300)
}
function onTableUpdate(options) { currentOptions = options; fetchData() }
onMounted(fetchData)
</script>
