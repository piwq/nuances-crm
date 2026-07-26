<template>
  <div>
    <page-header title="Учёт времени" :subtitle="summaryText">
      <v-btn variant="tonal" prepend-icon="mdi-download" class="mr-2" :loading="exporting" @click="exportCsv">CSV</v-btn>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openDialog()">Добавить запись</v-btn>
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
            <date-field v-model="filters.date_from" label="С" clearable hide-details @update:model-value="fetchData" />
          </v-col>
          <v-col cols="6" md="2">
            <date-field v-model="filters.date_to" label="По" clearable hide-details @update:model-value="fetchData" />
          </v-col>
          <v-col cols="6" md="2">
            <v-select
              v-model="filters.is_billable"
              :items="billableOptions"
              item-value="value"
              item-title="title"
              label="Биллинг"
              clearable
              hide-details
              @update:model-value="fetchData"
            />
          </v-col>
          <v-col cols="6" md="2">
            <v-select
              v-model="filters.unbilled"
              :items="unbilledOptions"
              item-value="value"
              item-title="title"
              label="Выставлено"
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
        :items="store.timeEntries"
        :items-length="store.pagination.total"
        :loading="store.loading"
        :items-per-page="25"
        @update:options="onTableUpdate"
      >
        <template #item.date="{ item }">{{ formatDate(item.date) }}</template>

        <template #item.hours="{ item }">
          <span class="font-weight-medium">{{ formatHours(item.hours) }}</span>
        </template>

        <template #item.is_billable="{ item }">
          <v-icon :color="item.is_billable ? 'success' : 'grey'" :icon="item.is_billable ? 'mdi-check-circle' : 'mdi-circle-outline'" size="18" />
        </template>

        <template #item.is_invoiced="{ item }">
          <v-icon :color="item.is_invoiced ? 'success' : 'grey'" :icon="item.is_invoiced ? 'mdi-check-circle' : 'mdi-circle-outline'" size="18" />
        </template>

        <template #item.amount="{ item }">
          {{ item.is_billable ? formatCurrency(item.amount) : '—' }}
        </template>

        <template #item.actions="{ item }">
          <div class="d-flex gap-1 justify-end">
            <v-btn icon="mdi-pencil" size="small" variant="text" color="primary" :disabled="item.is_invoiced" @click="openDialog(item)" />
            <v-btn icon="mdi-delete" size="small" variant="text" color="error" :disabled="item.is_invoiced" @click="handleDelete(item)" />
          </div>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- Dialog -->
    <form-dialog v-model="dialog.show" max-width="520">
      <v-card>
        <v-card-title>{{ dialog.entry ? 'Редактировать запись' : 'Новая запись времени' }}</v-card-title>
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
            />
            <v-row dense>
              <v-col cols="6">
                <date-field v-model="form.date" label="Дата *" :rules="[required]" class="mb-2" />
              </v-col>
              <v-col cols="6">
                <v-text-field
                  v-model.number="form.hours"
                  label="Часов *"
                  type="number"
                  step="0.25"
                  min="0.25"
                  :rules="[required, positiveNum]"
                  class="mb-2"
                />
              </v-col>
            </v-row>
            <v-textarea v-model="form.description" label="Описание" rows="2" auto-grow class="mb-2" />
            <v-row dense>
              <v-col cols="6">
                <v-text-field
                  v-model.number="form.hourly_rate"
                  label="Ставка (₽/ч)"
                  type="number"
                  min="0"
                  class="mb-2"
                />
              </v-col>
              <v-col cols="6" class="d-flex align-center">
                <v-checkbox v-model="form.is_billable" label="Биллинговая" hide-details />
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>
        <v-divider />
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog.show = false">Отмена</v-btn>
          <v-btn color="primary" variant="tonal" :loading="saving" @click="handleSave">
            {{ dialog.entry ? 'Сохранить' : 'Добавить' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </form-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useBillingStore } from '@/stores/billing'
import { useNotification } from '@/composables/useNotification'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { formatDate, formatHours, formatCurrency } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import api from '@/plugins/axios'
import FormDialog from '@/components/common/FormDialog.vue'
import DateField from '@/components/common/DateField.vue'

const route = useRoute()
const store = useBillingStore()
const { success, error } = useNotification()
const { confirm } = useConfirmDialog()

const filters = ref({ case: null, date_from: '', date_to: '', is_billable: '', unbilled: '' })
// переход «Управлять временем» из карточки дела приносит ?case=<id>
if (route.query.case) filters.value.case = Number(route.query.case)
let currentOptions = { page: 1, itemsPerPage: 25, sortBy: [] }

const cases = ref([])
const loadingCases = ref(false)
const formRef = ref(null)
const saving = ref(false)
const exporting = ref(false)
const dialog = ref({ show: false, entry: null })
const form = ref(emptyForm())

const required = v => !!v || 'Обязательное поле'
const positiveNum = v => (v > 0) || 'Должно быть больше 0'

const billableOptions = [{ value: '', title: 'Все' }, { value: 'true', title: 'Биллинговые' }, { value: 'false', title: 'Небиллинговые' }]
const unbilledOptions = [{ value: '', title: 'Все' }, { value: 'true', title: 'Не выставлено' }, { value: 'false', title: 'Выставлено' }]

const totalHours = computed(() => store.timeEntries.reduce((s, e) => s + parseFloat(e.hours || 0), 0))
const summaryText = computed(() => {
  if (!store.timeEntries.length) return ''
  return `На странице: ${formatHours(totalHours.value)}`
})

const headers = [
  { title: 'Дата', key: 'date', sortable: true },
  { title: 'Дело', key: 'case_title', sortable: false },
  { title: 'Юрист', key: 'lawyer_name', sortable: false },
  { title: 'Часы', key: 'hours', sortable: true },
  { title: 'Описание', key: 'description', sortable: false },
  { title: 'Биллинг', key: 'is_billable', sortable: false },
  { title: 'Выставлено', key: 'is_invoiced', sortable: false },
  { title: 'Сумма', key: 'amount', sortable: false },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

function emptyForm() {
  return { case: null, date: new Date().toISOString().slice(0, 10), hours: 1, description: '', hourly_rate: null, is_billable: true }
}

function buildParams() {
  const params = { page: currentOptions.page, page_size: currentOptions.itemsPerPage }
  if (filters.value.case) params.case = filters.value.case
  if (filters.value.date_from) params.date_from = filters.value.date_from
  if (filters.value.date_to) params.date_to = filters.value.date_to
  if (filters.value.is_billable !== '') params.is_billable = filters.value.is_billable
  if (filters.value.unbilled !== '') params.unbilled = filters.value.unbilled
  if (currentOptions.sortBy?.length) {
    const s = currentOptions.sortBy[0]
    params.ordering = s.order === 'desc' ? `-${s.key}` : s.key
  }
  return params
}

function fetchData() { store.fetchTimeEntries(buildParams()) }
function onTableUpdate(options) { currentOptions = options; fetchData() }

async function exportCsv() {
  exporting.value = true
  try {
    const params = { ...buildParams() }
    delete params.page
    delete params.page_size
    const { data } = await api.get('/api/v1/billing/time-entries/export/', { params, responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([data]))
    const a = document.createElement('a')
    a.href = url
    a.download = 'time_entries.csv'
    a.click()
    URL.revokeObjectURL(url)
  } finally {
    exporting.value = false
  }
}

async function loadCases() {
  if (cases.value.length) return
  loadingCases.value = true
  try {
    const { data } = await api.get('/api/v1/cases/', { params: { page_size: 200 } })
    cases.value = data.results || data
  } finally {
    loadingCases.value = false
  }
}

function openDialog(entry = null) {
  dialog.value.entry = entry
  form.value = entry
    ? { case: entry.case, date: entry.date, hours: entry.hours, description: entry.description, hourly_rate: entry.hourly_rate, is_billable: entry.is_billable }
    : emptyForm()
  dialog.value.show = true
  loadCases()
}

async function handleSave() {
  const { valid } = await formRef.value.validate()
  if (!valid) return
  saving.value = true
  try {
    if (dialog.value.entry) {
      await store.updateTimeEntry(dialog.value.entry.id, form.value)
      success('Запись обновлена')
    } else {
      await store.createTimeEntry(form.value)
      success('Запись добавлена')
    }
    dialog.value.show = false
    fetchData()
  } catch {
    error('Ошибка сохранения')
  } finally {
    saving.value = false
  }
}

async function handleDelete(entry) {
  const ok = await confirm('Удалить запись?', `${formatDate(entry.date)} — ${formatHours(entry.hours)}`)
  if (!ok) return
  try {
    await store.deleteTimeEntry(entry.id)
    success('Запись удалена')
    fetchData()
  } catch {
    error('Ошибка удаления')
  }
}

loadCases()
fetchData()
</script>
