<template>
  <div>
    <page-header title="Счета" :subtitle="`Всего: ${store.pagination.total}`">
      <v-btn variant="tonal" prepend-icon="mdi-download" class="mr-2" :loading="exporting" @click="exportCsv">CSV</v-btn>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openDialog()">Новый счёт</v-btn>
    </page-header>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row dense>
          <v-col cols="12" md="3">
            <v-autocomplete
              v-model="filters.case"
              :items="cases"
              item-title="title"
              item-value="id"
              label="Дело"
              clearable
              hide-details
              :loading="loadingCases"
              @update:model-value="fetchData"
            />
          </v-col>
          <v-col cols="6" md="2">
            <v-select
              v-model="filters.status"
              :items="statusOptions"
              item-value="value"
              item-title="title"
              label="Статус"
              clearable
              hide-details
              @update:model-value="fetchData"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <v-card>
      <v-data-table-server
        :headers="headers"
        :items="store.invoices"
        :items-length="store.pagination.total"
        :loading="store.loading"
        :items-per-page="25"
        @update:options="onTableUpdate"
      >
        <template #item.invoice_number="{ item }">
          <router-link :to="`/billing/invoices/${item.id}`" class="text-primary font-weight-medium text-decoration-none">
            {{ item.invoice_number }}
          </router-link>
        </template>

        <template #item.status="{ item }">
          <status-chip :value="item.status" :options="INVOICE_STATUSES" />
        </template>

        <template #item.issue_date="{ item }">{{ formatDate(item.issue_date) }}</template>
        <template #item.due_date="{ item }">
          <span :class="isOverdue(item) ? 'text-error font-weight-medium' : ''">
            {{ formatDate(item.due_date) }}
          </span>
        </template>

        <template #item.total="{ item }">
          <span class="font-weight-medium">{{ formatCurrency(item.total) }}</span>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- Create Dialog -->
    <form-dialog v-model="dialog.show" max-width="520">
      <v-card>
        <v-card-title>Новый счёт</v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <v-form ref="formRef" @submit.prevent="handleSave">
            <v-autocomplete
              v-model="form.case"
              :items="cases"
              item-title="title"
              item-value="id"
              label="Дело *"
              :rules="[required]"
              :loading="loadingCases"
              class="mb-2"
              @update:model-value="onCaseChange"
            />
            <v-autocomplete
              v-model="form.client"
              :items="clients"
              item-title="display_name"
              item-value="id"
              label="Клиент *"
              :rules="[required]"
              :loading="loadingClients"
              class="mb-2"
            />
            <v-row dense>
              <v-col cols="6">
                <date-field v-model="form.issue_date" label="Дата выставления *" :rules="[required]" class="mb-2" />
              </v-col>
              <v-col cols="6">
                <date-field v-model="form.due_date" label="Срок оплаты" class="mb-2" />
              </v-col>
            </v-row>
            <v-text-field v-model.number="form.tax_rate" label="Ставка НДС (%)" type="number" min="0" max="100" class="mb-2" />
            <v-textarea v-model="form.notes" label="Примечания" rows="2" auto-grow />
          </v-form>
        </v-card-text>
        <v-divider />
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog.show = false">Отмена</v-btn>
          <v-btn color="primary" variant="tonal" :loading="saving" @click="handleSave">Создать</v-btn>
        </v-card-actions>
      </v-card>
    </form-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { isBefore, parseISO, startOfToday } from 'date-fns'
import { useRoute, useRouter } from 'vue-router'
import { useBillingStore } from '@/stores/billing'
import { useNotification } from '@/composables/useNotification'
import { formatDate, formatCurrency } from '@/utils/formatters'
import { INVOICE_STATUSES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusChip from '@/components/common/StatusChip.vue'
import api from '@/plugins/axios'
import FormDialog from '@/components/common/FormDialog.vue'
import DateField from '@/components/common/DateField.vue'

const store = useBillingStore()
const route = useRoute()
const router = useRouter()
const { success, error } = useNotification()

const filters = ref({ case: null, status: '' })
// переход «Перейти к счетам» из карточки дела приносит ?case=<id>
if (route.query.case) filters.value.case = Number(route.query.case)
let currentOptions = { page: 1, itemsPerPage: 25, sortBy: [] }

const cases = ref([])
const clients = ref([])
const loadingCases = ref(false)
const loadingClients = ref(false)
const formRef = ref(null)
const saving = ref(false)
const exporting = ref(false)
const dialog = ref({ show: false })
const form = ref(emptyForm())

const required = v => !!v || 'Обязательное поле'
const statusOptions = [{ value: '', title: 'Все' }, ...INVOICE_STATUSES.map(s => ({ value: s.value, title: s.label }))]

const headers = [
  { title: '№ счёта', key: 'invoice_number', sortable: true },
  { title: 'Дело', key: 'case_title', sortable: false },
  { title: 'Клиент', key: 'client_name', sortable: false },
  { title: 'Статус', key: 'status', sortable: false },
  { title: 'Выставлен', key: 'issue_date', sortable: true },
  { title: 'Срок оплаты', key: 'due_date', sortable: true },
  { title: 'Сумма', key: 'total', sortable: true },
]

function emptyForm() {
  return {
    case: null,
    client: null,
    issue_date: new Date().toISOString().slice(0, 10),
    due_date: '',
    tax_rate: 0,
    notes: '',
  }
}

function isOverdue(invoice) {
  return invoice.due_date &&
    invoice.status !== 'paid' &&
    invoice.status !== 'cancelled' &&
    isBefore(parseISO(invoice.due_date), startOfToday())
}

function buildParams() {
  const params = { page: currentOptions.page, page_size: currentOptions.itemsPerPage }
  if (filters.value.case) params.case = filters.value.case
  if (filters.value.status) params.status = filters.value.status
  if (currentOptions.sortBy?.length) {
    const s = currentOptions.sortBy[0]
    params.ordering = s.order === 'desc' ? `-${s.key}` : s.key
  }
  return params
}

function fetchData() { store.fetchInvoices(buildParams()) }
function onTableUpdate(options) { currentOptions = options; fetchData() }

async function exportCsv() {
  exporting.value = true
  try {
    const params = { ...buildParams() }
    delete params.page
    delete params.page_size
    const { data } = await api.get('/api/v1/billing/invoices/export/', { params, responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([data]))
    const a = document.createElement('a')
    a.href = url
    a.download = 'invoices.csv'
    a.click()
    URL.revokeObjectURL(url)
  } finally {
    exporting.value = false
  }
}

async function loadFormData() {
  loadingCases.value = true
  loadingClients.value = true
  try {
    const [casesRes, clientsRes] = await Promise.all([
      api.get('/api/v1/cases/', { params: { page_size: 200 } }),
      api.get('/api/v1/clients/', { params: { page_size: 200 } }),
    ])
    cases.value = casesRes.data.results || casesRes.data
    clients.value = clientsRes.data.results || clientsRes.data
  } finally {
    loadingCases.value = false
    loadingClients.value = false
  }
}

function onCaseChange(caseId) {
  const c = cases.value.find(c => c.id === caseId)
  if (c?.client) form.value.client = c.client
}

function openDialog() {
  form.value = emptyForm()
  dialog.value.show = true
  loadFormData()
}

async function handleSave() {
  const { valid } = await formRef.value.validate()
  if (!valid) return
  saving.value = true
  try {
    const created = await store.createInvoice(form.value)
    success('Счёт создан')
    dialog.value.show = false
    router.push(`/billing/invoices/${created.id}`)
  } catch {
    error('Ошибка создания счёта')
  } finally {
    saving.value = false
  }
}

fetchData()
</script>
