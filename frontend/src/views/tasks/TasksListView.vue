<template>
  <div>
    <page-header title="Задачи" :subtitle="`Всего: ${store.pagination.total}`">
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openDialog()">Новая задача</v-btn>
    </page-header>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row dense>
          <v-col cols="12" md="4">
            <v-text-field
              v-model="search"
              label="Поиск..."
              prepend-inner-icon="mdi-magnify"
              clearable
              hide-details
              @update:model-value="debouncedFetch"
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
          <v-col cols="6" md="2">
            <v-select
              v-model="filters.priority"
              :items="priorityOptions"
              item-value="value"
              item-title="title"
              label="Приоритет"
              clearable
              hide-details
              @update:model-value="fetchData"
            />
          </v-col>
          <v-col cols="6" md="2">
            <v-select
              v-model="filters.assigned_to"
              :items="lawyerOptions"
              item-value="value"
              item-title="title"
              label="Исполнитель"
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
        :items="store.tasks"
        :items-length="store.pagination.total"
        :loading="store.loading"
        :items-per-page="25"
        @update:options="onTableUpdate"
      >
        <template #item.title="{ item }">
          <div class="font-weight-medium">{{ item.title }}</div>
          <div v-if="item.case_title" class="text-caption text-medium-emphasis">
            <v-icon size="12" class="mr-1">mdi-briefcase-outline</v-icon>{{ item.case_title }}
          </div>
        </template>

        <template #item.priority="{ item }">
          <status-chip :value="item.priority" :options="TASK_PRIORITIES" />
        </template>

        <template #item.status="{ item }">
          <status-chip :value="item.status" :options="TASK_STATUSES" />
        </template>

        <template #item.due_date="{ item }">
          <span :class="isOverdue(item) ? 'text-error font-weight-medium' : ''">
            {{ formatDate(item.due_date) }}
            <v-icon v-if="isOverdue(item)" size="14" class="ml-1">mdi-alert-circle</v-icon>
          </span>
        </template>

        <template #item.assigned_to_name="{ item }">
          {{ item.assigned_to_name || '—' }}
        </template>

        <template #item.actions="{ item }">
          <div class="d-flex gap-1">
            <v-btn
              v-if="item.status !== 'done' && item.status !== 'cancelled'"
              icon="mdi-check"
              size="small"
              variant="text"
              color="success"
              title="Выполнено"
              @click="handleComplete(item)"
            />
            <v-btn
              icon="mdi-pencil"
              size="small"
              variant="text"
              color="primary"
              title="Редактировать"
              @click="openDialog(item)"
            />
            <v-btn
              icon="mdi-delete"
              size="small"
              variant="text"
              color="error"
              title="Удалить"
              @click="handleDelete(item)"
            />
          </div>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- Task Dialog -->
    <form-dialog v-model="dialog.show" max-width="600">
      <v-card>
        <v-card-title>{{ dialog.task ? 'Редактировать задачу' : 'Новая задача' }}</v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <v-form ref="formRef" @submit.prevent="handleSave">
            <v-text-field
              v-model="form.title"
              label="Название *"
              :rules="[required]"
              class="mb-2"
            />
            <v-textarea
              v-model="form.description"
              label="Описание"
              rows="2"
              auto-grow
              class="mb-2"
            />
            <v-row dense>
              <v-col cols="12" md="6">
                <v-autocomplete
                  v-model="form.case"
                  :items="cases"
                  item-title="title"
                  item-value="id"
                  label="Дело"
                  clearable
                  :loading="loadingCases"
                  class="mb-2"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-select
                  v-model="form.assigned_to"
                  :items="lawyers"
                  item-title="full_name"
                  item-value="id"
                  label="Исполнитель"
                  clearable
                  :loading="loadingLawyers"
                  class="mb-2"
                />
              </v-col>
            </v-row>
            <v-row dense>
              <v-col cols="6" md="4">
                <v-select
                  v-model="form.priority"
                  :items="TASK_PRIORITIES"
                  item-title="label"
                  item-value="value"
                  label="Приоритет"
                  class="mb-2"
                />
              </v-col>
              <v-col cols="6" md="4">
                <v-select
                  v-model="form.status"
                  :items="TASK_STATUSES"
                  item-title="label"
                  item-value="value"
                  label="Статус"
                  class="mb-2"
                />
              </v-col>
              <v-col cols="12" md="4">
                <date-field
                  v-model="form.due_date"
                  label="Срок"
                  class="mb-2" />
              </v-col>
              <v-col cols="12">
                <v-select
                  v-model="form.recurrence"
                  :items="TASK_RECURRENCES"
                  item-title="label"
                  item-value="value"
                  label="Повторение"
                  :hint="form.recurrence !== 'none' ? 'После выполнения автоматически создастся следующая задача' : ''"
                  persistent-hint
                />
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>
        <v-divider />
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog.show = false">Отмена</v-btn>
          <v-btn color="primary" variant="elevated" :loading="saving" @click="handleSave">
            {{ dialog.task ? 'Сохранить' : 'Создать' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </form-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { isBefore, parseISO, startOfToday } from 'date-fns'
import { useTasksStore } from '@/stores/tasks'
import { useNotification } from '@/composables/useNotification'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { formatDate } from '@/utils/formatters'
import { TASK_PRIORITIES, TASK_STATUSES, TASK_RECURRENCES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusChip from '@/components/common/StatusChip.vue'
import api from '@/plugins/axios'
import FormDialog from '@/components/common/FormDialog.vue'
import DateField from '@/components/common/DateField.vue'

const store = useTasksStore()
const { success, error } = useNotification()
const { confirm } = useConfirmDialog()

const search = ref('')
const filters = ref({ status: '', priority: '', assigned_to: '' })
let currentOptions = { page: 1, itemsPerPage: 25, sortBy: [] }
let searchTimeout = null

const cases = ref([])
const lawyers = ref([])
const loadingCases = ref(false)
const loadingLawyers = ref(false)

const formRef = ref(null)
const saving = ref(false)
const dialog = ref({ show: false, task: null })
const form = ref(emptyForm())

const required = v => !!v || 'Обязательное поле'

function emptyForm() {
  return { title: '', description: '', case: null, assigned_to: null, priority: 'medium', status: 'todo', due_date: null, recurrence: 'none' }
}

const statusOptions = [{ value: '', title: 'Все' }, ...TASK_STATUSES.map(s => ({ value: s.value, title: s.label }))]
const priorityOptions = [{ value: '', title: 'Все' }, ...TASK_PRIORITIES.map(p => ({ value: p.value, title: p.label }))]
const lawyerOptions = ref([{ value: '', title: 'Все' }])

const headers = [
  { title: 'Задача', key: 'title', sortable: false },
  { title: 'Приоритет', key: 'priority', sortable: false },
  { title: 'Статус', key: 'status', sortable: false },
  { title: 'Срок', key: 'due_date', sortable: true },
  { title: 'Исполнитель', key: 'assigned_to_name', sortable: false },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

function isOverdue(task) {
  return task.due_date &&
    task.status !== 'done' &&
    task.status !== 'cancelled' &&
    isBefore(parseISO(task.due_date), startOfToday())
}

function buildParams() {
  const params = { page: currentOptions.page, page_size: currentOptions.itemsPerPage }
  if (search.value) params.search = search.value
  if (filters.value.status) params.status = filters.value.status
  if (filters.value.priority) params.priority = filters.value.priority
  if (filters.value.assigned_to) params.assigned_to = filters.value.assigned_to
  if (currentOptions.sortBy?.length) {
    const s = currentOptions.sortBy[0]
    params.ordering = s.order === 'desc' ? `-${s.key}` : s.key
  }
  return params
}

function fetchData() { store.fetchTasks(buildParams()) }
function debouncedFetch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(fetchData, 300)
}
function onTableUpdate(options) { currentOptions = options; fetchData() }

async function loadFormData() {
  if (cases.value.length && lawyers.value.length) return
  loadingCases.value = true
  loadingLawyers.value = true
  try {
    const [casesRes, lawyersRes] = await Promise.all([
      api.get('/api/v1/cases/', { params: { page_size: 200 } }),
      api.get('/api/v1/users/lawyers/'),
    ])
    cases.value = casesRes.data.results || casesRes.data
    lawyers.value = lawyersRes.data.map(l => ({
      ...l,
      full_name: `${l.last_name} ${l.first_name}`.trim() || l.username,
    }))
    lawyerOptions.value = [
      { value: '', title: 'Все' },
      ...lawyers.value.map(l => ({ value: l.id, title: l.full_name })),
    ]
  } catch {
    error('Ошибка загрузки данных')
  } finally {
    loadingCases.value = false
    loadingLawyers.value = false
  }
}

function openDialog(task = null) {
  dialog.value.task = task
  form.value = task
    ? { title: task.title, description: task.description || '', case: task.case, assigned_to: task.assigned_to, priority: task.priority, status: task.status, due_date: task.due_date }
    : emptyForm()
  dialog.value.show = true
  loadFormData()
}

async function handleSave() {
  const { valid } = await formRef.value.validate()
  if (!valid) return
  saving.value = true
  try {
    if (dialog.value.task) {
      await store.updateTask(dialog.value.task.id, form.value)
      success('Задача обновлена')
    } else {
      await store.createTask(form.value)
      success('Задача создана')
    }
    dialog.value.show = false
    fetchData()
  } catch {
    error('Ошибка сохранения')
  } finally {
    saving.value = false
  }
}

async function handleComplete(task) {
  try {
    await store.completeTask(task.id)
    success('Задача выполнена')
    fetchData()
  } catch {
    error('Ошибка')
  }
}

async function handleDelete(task) {
  const ok = await confirm('Удалить задачу?', `"${task.title}" будет удалена безвозвратно.`)
  if (!ok) return
  try {
    await store.deleteTask(task.id)
    success('Задача удалена')
    fetchData()
  } catch {
    error('Ошибка удаления')
  }
}

onMounted(fetchData)
</script>
