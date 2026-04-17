<template>
  <div>
    <page-header title="Клиенты" :subtitle="`Всего: ${store.pagination.total}`">
      <v-btn color="primary" prepend-icon="mdi-plus" to="/clients/new">Добавить клиента</v-btn>
    </page-header>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row dense>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="search"
              label="Поиск по имени, компании, телефону..."
              prepend-inner-icon="mdi-magnify"
              clearable
              hide-details
              @update:model-value="debouncedFetch"
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-select
              v-model="filters.client_type"
              :items="[{ value: '', title: 'Все типы' }, { value: 'individual', title: 'Физлица' }, { value: 'legal_entity', title: 'Юрлица' }]"
              item-value="value"
              item-title="title"
              label="Тип клиента"
              hide-details
              clearable
              @update:model-value="fetchData"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Table -->
    <v-card>
      <v-data-table-server
        :headers="headers"
        :items="store.clients"
        :items-length="store.pagination.total"
        :loading="store.loading"
        :items-per-page="25"
        @update:options="onTableUpdate"
      >
        <template #item.display_name="{ item }">
          <router-link :to="`/clients/${item.id}`" class="text-primary font-weight-medium text-decoration-none">
            {{ item.display_name }}
          </router-link>
        </template>
        <template #item.client_type="{ item }">
          <v-chip size="small" :color="item.client_type === 'individual' ? 'blue' : 'purple'" variant="tonal">
            {{ item.client_type === 'individual' ? 'Физлицо' : 'Юрлицо' }}
          </v-chip>
        </template>
        <template #item.cases_count="{ item }">
          <v-chip size="small" color="primary" variant="tonal">{{ item.cases_count }}</v-chip>
        </template>
        <template #item.created_at="{ item }">
          {{ formatDate(item.created_at) }}
        </template>
        <template #item.actions="{ item }">
          <v-btn icon="mdi-pencil" size="small" variant="text" :to="`/clients/${item.id}/edit`" />
        </template>
      </v-data-table-server>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useClientsStore } from '@/stores/clients'
import { formatDate } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'

const store = useClientsStore()
const search = ref('')
const filters = ref({ client_type: '' })
let searchTimeout = null

const headers = [
  { title: 'Клиент', key: 'display_name', sortable: true },
  { title: 'Тип', key: 'client_type', sortable: false },
  { title: 'Email', key: 'email', sortable: false },
  { title: 'Телефон', key: 'phone', sortable: false },
  { title: 'Дел', key: 'cases_count', sortable: false },
  { title: 'Добавлен', key: 'created_at', sortable: true },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

let currentOptions = { page: 1, itemsPerPage: 25, sortBy: [] }

function buildParams() {
  const params = {
    page: currentOptions.page,
    page_size: currentOptions.itemsPerPage,
  }
  if (search.value) params.search = search.value
  if (filters.value.client_type) params.client_type = filters.value.client_type
  if (currentOptions.sortBy?.length) {
    const s = currentOptions.sortBy[0]
    params.ordering = s.order === 'desc' ? `-${s.key}` : s.key
  }
  return params
}

function fetchData() {
  store.fetchClients(buildParams())
}

function debouncedFetch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(fetchData, 300)
}

function onTableUpdate(options) {
  currentOptions = options
  fetchData()
}

onMounted(fetchData)
</script>
