<template>
  <div v-if="caseItem">
    <page-header :title="caseItem.title" :subtitle="caseItem.case_number">
      <template #default>
        <div class="d-flex align-center gap-2 flex-wrap">
          <v-btn variant="outlined" prepend-icon="mdi-pencil" :to="`/cases/${caseItem.uuid}/edit`">
            Редактировать
          </v-btn>
          <v-btn v-if="auth.isAdmin" color="error" variant="outlined" prepend-icon="mdi-delete-outline" @click="deleteCase">
            Удалить
          </v-btn>
          <v-menu>
            <template #activator="{ props }">
              <v-btn v-bind="props" variant="tonal" append-icon="mdi-chevron-down" :loading="statusChanging">
                <status-chip :value="caseItem.status" :options="CASE_STATUSES" />
              </v-btn>
            </template>
            <v-list density="compact" min-width="180">
              <v-list-item
                v-for="s in CASE_STATUSES"
                :key="s.value"
                :disabled="s.value === caseItem.status"
                @click="handleStatusChange(s.value)"
              >
                <status-chip :value="s.value" :options="CASE_STATUSES" />
              </v-list-item>
            </v-list>
          </v-menu>
        </div>
      </template>
    </page-header>

    <v-alert
      v-if="deadlineInfo"
      :type="deadlineInfo.type"
      variant="tonal"
      density="comfortable"
      :icon="deadlineInfo.icon"
      class="mb-4"
    >
      <strong>{{ deadlineInfo.label }}:</strong> {{ formatDate(caseItem.key_deadline) }}<span v-if="caseItem.key_deadline_note"> — {{ caseItem.key_deadline_note }}</span>
    </v-alert>

    <v-tabs v-model="tab" color="primary" class="mb-4 border-b">
      <v-tab value="info">Инфо</v-tab>
      <v-tab value="documents">Документы ({{ documentsStore.documents.length }})</v-tab>
      <v-tab value="tasks">Задачи ({{ openTasksCount }})</v-tab>
      <v-tab value="billing">Биллинг</v-tab>
      <v-tab value="notes" @click="loadNotes">Заметки ({{ notes.length }})</v-tab>
      <v-tab value="history" @click="loadHistory">История</v-tab>
    </v-tabs>

    <v-window v-model="tab">
      <!-- Info Tab -->
      <v-window-item value="info">
        <v-row>
          <v-col cols="12" md="8">
            <v-card class="mb-4">
              <v-card-title>Детали дела</v-card-title>
              <v-card-text>
                <div class="text-body-1 mb-4">{{ caseItem.description || 'Нет описания' }}</div>
                <v-divider class="mb-4" />
                <v-row>
                  <v-col cols="6">
                    <div class="text-caption text-medium-emphasis">Категория</div>
                    <div>{{ categoryLabel }}</div>
                  </v-col>
                  <v-col cols="6">
                    <div class="text-caption text-medium-emphasis">Открыто</div>
                    <div>{{ formatDate(caseItem.opened_at) }}</div>
                  </v-col>
                </v-row>
                <v-row v-if="caseItem.court_name">
                  <v-col cols="6">
                    <div class="text-caption text-medium-emphasis">Суд</div>
                    <div>{{ caseItem.court_name }}</div>
                  </v-col>
                  <v-col cols="6">
                    <div class="text-caption text-medium-emphasis">Номер в суде</div>
                    <div>{{ caseItem.court_case_number }}</div>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="4">
            <v-card class="mb-4" :to="caseItem.client_detail ? `/clients/${caseItem.client_detail.uuid}` : undefined">
              <v-card-title>Клиент</v-card-title>
              <v-card-text v-if="caseItem.client_detail">
                <div class="text-h6 text-primary">{{ caseItem.client_detail.display_name }}</div>
                <div class="text-body-2 text-medium-emphasis">
                  {{ caseItem.client_detail.email }}<br />
                  {{ caseItem.client_detail.phone }}
                </div>
              </v-card-text>
            </v-card>
            <v-card>
              <v-card-title class="d-flex justify-space-between align-center">
                Команда
                <v-btn v-if="auth.isAdmin" size="small" variant="tonal" color="primary" prepend-icon="mdi-account-plus" @click="openAssignDialog">
                  Назначить
                </v-btn>
              </v-card-title>
              <v-list density="compact">
                <v-list-item v-if="caseItem.lead_lawyer_detail" :title="`${caseItem.lead_lawyer_detail.last_name} ${caseItem.lead_lawyer_detail.first_name}`" subtitle="Ответственный юрист" prepend-icon="mdi-account-star" />
                <v-list-item v-for="lawyer in caseItem.assigned_lawyers_detail" :key="lawyer.id" :title="`${lawyer.last_name} ${lawyer.first_name}`" subtitle="Юрист" prepend-icon="mdi-account">
                  <template #append>
                    <v-btn v-if="auth.isAdmin" icon="mdi-close" size="x-small" variant="text" @click="unassignLawyer(lawyer)" />
                  </template>
                </v-list-item>
              </v-list>
            </v-card>
          </v-col>
        </v-row>
      </v-window-item>

      <!-- Documents Tab -->
      <v-window-item value="documents">
        <v-card
          class="drop-zone"
          :class="{ 'drop-zone--active': isDragOver }"
          @dragover.prevent="isDragOver = true"
          @dragleave="isDragOver = false"
          @drop.prevent="onFileDrop"
        >
          <v-card-title class="d-flex justify-space-between align-center">
            Документы
            <div class="d-flex align-center gap-2">
              <span v-if="uploading" class="text-caption text-medium-emphasis">
                <v-progress-circular size="14" width="2" indeterminate class="mr-1" />
                Загрузка...
              </span>
              <v-btn color="secondary" prepend-icon="mdi-file-document-plus-outline" variant="tonal" size="small" @click="openTemplateDialog">Из шаблона</v-btn>
              <v-btn color="primary" prepend-icon="mdi-upload" variant="tonal" size="small" @click="docDialog = true">Загрузить</v-btn>
            </div>
          </v-card-title>
          <v-list v-if="documentsStore.documents.length">
            <v-list-item v-for="doc in documentsStore.documents" :key="doc.id" :title="doc.title" :subtitle="formatDate(doc.uploaded_at)">
              <template #prepend>
                <v-icon :icon="fileIcon(doc.file)" class="mr-3" />
              </template>
              <template #append>
                <v-btn v-if="isPreviewable(doc)" icon="mdi-eye-outline" variant="text" size="small" @click="previewDoc(doc)" />
                <v-btn icon="mdi-download" variant="text" size="small" @click="documentsStore.downloadDocument(doc.uuid, doc.title)" />
                <v-btn icon="mdi-delete" variant="text" size="small" color="error" @click="deleteDoc(doc)" />
              </template>
            </v-list-item>
          </v-list>
          <v-card-text v-else class="text-center pa-12 text-medium-emphasis">
            <v-icon size="48" class="mb-2">mdi-cloud-upload-outline</v-icon>
            <div>Перетащите файлы сюда или нажмите «Загрузить»</div>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- Tasks Tab -->
      <v-window-item value="tasks">
        <v-card>
          <v-card-title class="d-flex justify-space-between align-center">
            Задачи
            <div class="d-flex gap-2">
              <v-btn variant="text" size="small" to="/tasks">Все задачи</v-btn>
              <v-btn color="primary" prepend-icon="mdi-plus" variant="tonal" size="small" @click="openTaskDialog">
                Новая задача
              </v-btn>
            </div>
          </v-card-title>
          <v-list v-if="caseTasks.length">
            <v-list-item v-for="task in caseTasks" :key="task.id" :title="task.title" :subtitle="`Срок: ${formatDate(task.due_date)}`">
              <template #prepend>
                <v-checkbox-btn :model-value="task.status === 'done'" @update:model-value="toggleTask(task)" />
              </template>
              <template #append>
                <v-chip size="x-small" :color="taskPriorityColor(task.priority)" class="mr-2">{{ task.priority }}</v-chip>
                <status-chip :value="task.status" :options="TASK_STATUSES" size="x-small" />
              </template>
            </v-list-item>
          </v-list>
          <v-card-text v-else class="text-center pa-12 text-medium-emphasis">Нет текущих задач</v-card-text>
        </v-card>
      </v-window-item>

      <!-- Billing Tab -->
      <v-window-item value="billing">
        <v-row>
          <v-col cols="12" md="6">
            <v-card class="mb-4">
              <v-card-title>Учёт времени</v-card-title>
              <v-card-text>
                <div class="text-h4 mb-2">{{ totalHours }} ч.</div>
                <div class="text-subtitle-1 text-medium-emphasis mb-4">Всего зафиксировано времени по делу</div>
                <v-btn color="primary" block :to="{ path: '/billing/time', query: { case: caseItem.id } }">Управлять временем</v-btn>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="6">
            <v-card>
              <v-card-title>Счета</v-card-title>
              <v-card-text v-if="caseInvoices.length">
                <v-list density="compact">
                  <v-list-item v-for="inv in caseInvoices" :key="inv.id" :title="inv.invoice_number" :subtitle="formatDate(inv.issue_date)" :to="`/billing/invoices/${inv.id}`">
                    <template #append>
                      <status-chip :value="inv.status" :options="INVOICE_STATUSES" />
                    </template>
                  </v-list-item>
                </v-list>
              </v-card-text>
              <v-card-text v-else class="text-center pa-4 text-medium-emphasis">Нет выставленных счетов</v-card-text>
              <v-divider />
              <v-card-actions>
                <v-btn variant="text" block :to="{ path: '/billing/invoices', query: { case: caseItem.id } }">Перейти к счетам</v-btn>
              </v-card-actions>
            </v-card>
          </v-col>
        </v-row>
      </v-window-item>

      <!-- Notes Tab -->
      <v-window-item value="notes">
        <v-card>
          <v-card-title>Заметки</v-card-title>
          <v-divider />
          <div v-if="notesLoading" class="d-flex justify-center pa-8">
            <v-progress-circular indeterminate color="primary" />
          </div>
          <v-list v-else-if="notes.length" lines="two">
            <v-list-item v-for="note in notes" :key="note.id">
              <template #prepend>
                <v-avatar color="primary" size="36" class="mr-3">
                  <span class="text-body-2 font-weight-bold">{{ note.author_initials }}</span>
                </v-avatar>
              </template>
              <v-list-item-title class="text-body-2 font-weight-medium">{{ note.author_name }}</v-list-item-title>
              <v-list-item-subtitle class="text-body-2 mt-1" style="white-space: pre-wrap; -webkit-line-clamp: unset; opacity: 1">{{ note.text }}</v-list-item-subtitle>
              <div class="text-caption text-medium-emphasis mt-1">{{ formatDateTime(note.created_at) }}</div>
              <template #append>
                <v-btn icon="mdi-delete-outline" variant="text" size="small" color="error" @click="deleteNote(note.id)" />
              </template>
            </v-list-item>
          </v-list>
          <v-card-text v-else class="text-center pa-8 text-medium-emphasis">
            <v-icon size="40" class="mb-2">mdi-note-outline</v-icon>
            <div>Заметок пока нет</div>
          </v-card-text>
          <v-divider />
          <v-card-text>
            <v-textarea
              v-model="newNoteText"
              label="Новая заметка"
              rows="2"
              auto-grow
              hide-details
              variant="outlined"
              density="compact"
              class="mb-2"
            />
            <v-btn color="primary" variant="tonal" size="small" :loading="noteSaving" :disabled="!newNoteText.trim()" @click="addNote">
              Добавить заметку
            </v-btn>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- History Tab -->
      <v-window-item value="history">
        <v-card>
          <v-card-title>История изменений</v-card-title>
          <v-divider />
          <div v-if="historyLoading" class="d-flex justify-center pa-8">
            <v-progress-circular indeterminate color="primary" />
          </div>
          <v-timeline v-else-if="history.length" density="compact" side="end" class="pa-4">
            <v-timeline-item
              v-for="entry in history"
              :key="entry.id"
              :dot-color="actionColor(entry.action)"
              size="x-small"
            >
              <div class="d-flex justify-space-between align-start">
                <div>
                  <div class="text-body-2 font-weight-medium">{{ entry.description }}</div>
                  <div class="text-caption text-medium-emphasis">{{ entry.user_name }}</div>
                </div>
                <div class="text-caption text-medium-emphasis ml-4 flex-shrink-0">{{ formatDateTime(entry.timestamp) }}</div>
              </div>
            </v-timeline-item>
          </v-timeline>
          <v-card-text v-else class="text-center pa-12 text-medium-emphasis">
            История изменений пуста
          </v-card-text>
        </v-card>
      </v-window-item>
    </v-window>

    <!-- Generate from Template Dialog -->
    <v-dialog v-model="templateDialog" max-width="500">
      <v-card>
        <v-card-title>Создать документ из шаблона</v-card-title>
        <v-card-text>
          <v-select
            v-model="selectedTemplate"
            :items="templates"
            item-title="name"
            item-value="id"
            label="Шаблон"
            :loading="templatesLoading"
            :no-data-text="templatesLoading ? 'Загрузка...' : 'Нет шаблонов — загрузите их в админке'"
          />
          <div class="text-caption text-medium-emphasis mt-1">
            Данные дела и клиента подставятся автоматически.
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="templateDialog = false">Отмена</v-btn>
          <v-btn color="primary" :loading="generating" :disabled="!selectedTemplate" @click="handleGenerate">Создать</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Upload Dialog -->
    <v-dialog v-model="docDialog" max-width="500">
      <v-card>
        <v-card-title>Загрузить документ</v-card-title>
        <v-card-text>
          <v-file-input v-model="newFile" label="Выберите файл" prepend-icon="mdi-file-upload" show-size border @update:model-value="onFilePicked" />
          <v-text-field v-model="newTitle" label="Название" class="mt-3" />
          <v-select
            v-model="newDocType"
            :items="DOCUMENT_TYPES"
            item-title="label"
            item-value="value"
            label="Тип документа"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="docDialog = false">Отмена</v-btn>
          <v-btn color="primary" :loading="uploading" :disabled="!pickedFile || !newTitle.trim()" @click="handleUpload">
            Загрузить
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Preview Dialog -->
    <v-dialog v-model="previewDialog" max-width="960" @after-leave="releasePreview">
      <v-card>
        <v-card-title class="d-flex justify-space-between align-center">
          <span class="text-truncate">{{ previewTitle }}</span>
          <v-btn icon="mdi-close" variant="text" @click="previewDialog = false" />
        </v-card-title>
        <v-card-text class="pa-0" style="height: 75vh">
          <iframe v-if="previewKind === 'pdf'" :src="previewUrl" style="width: 100%; height: 100%; border: 0" />
          <div v-else class="d-flex justify-center align-center pa-4" style="height: 100%">
            <img :src="previewUrl" style="max-width: 100%; max-height: 100%; object-fit: contain" />
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- New Task Dialog -->
    <v-dialog v-model="taskDialog" max-width="500">
      <v-card>
        <v-card-title>Новая задача по делу</v-card-title>
        <v-card-text>
          <v-text-field v-model="taskForm.title" label="Название" />
          <v-textarea v-model="taskForm.description" label="Описание" rows="2" auto-grow />
          <v-select
            v-model="taskForm.assigned_to"
            :items="lawyers"
            item-title="full_name"
            item-value="id"
            label="Исполнитель"
            clearable
          />
          <v-row dense>
            <v-col cols="6">
              <date-field v-model="taskForm.due_date" label="Срок" clearable />
            </v-col>
            <v-col cols="6">
              <v-select v-model="taskForm.priority" :items="TASK_PRIORITIES" item-title="label" item-value="value" label="Приоритет" />
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="taskDialog = false">Отмена</v-btn>
          <v-btn color="primary" :loading="taskSaving" :disabled="!taskForm.title.trim()" @click="createTask">Создать</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Assign Lawyer Dialog -->
    <v-dialog v-model="assignDialog" max-width="420">
      <v-card>
        <v-card-title>Назначить юриста</v-card-title>
        <v-card-text>
          <v-select
            v-model="assignLawyerId"
            :items="assignableLawyers"
            item-title="full_name"
            item-value="id"
            label="Юрист"
            :no-data-text="'Все юристы уже назначены'"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="assignDialog = false">Отмена</v-btn>
          <v-btn color="primary" :loading="assignSaving" :disabled="!assignLawyerId" @click="assignLawyer">Назначить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
  <div v-else-if="loading" class="d-flex justify-center mt-12">
    <v-progress-circular indeterminate color="primary" />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCasesStore } from '@/stores/cases'
import { useDocumentsStore } from '@/stores/documents'
import { useTasksStore } from '@/stores/tasks'
import { useBillingStore } from '@/stores/billing'
import { formatDate, formatDateTime } from '@/utils/formatters'
import { CASE_STATUSES, CASE_CATEGORIES, TASK_STATUSES, TASK_PRIORITIES, INVOICE_STATUSES, DOCUMENT_TYPES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusChip from '@/components/common/StatusChip.vue'
import { useNotification } from '@/composables/useNotification'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import api from '@/plugins/axios'
import DateField from '@/components/common/DateField.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const casesStore = useCasesStore()
const documentsStore = useDocumentsStore()
const tasksStore = useTasksStore()
const billingStore = useBillingStore()
const { success, error } = useNotification()
const { confirm: confirmDlg } = useConfirmDialog()

const caseItem = ref(null)
const loading = ref(true)
const statusChanging = ref(false)
const tab = ref('info')
const docDialog = ref(false)
const newFile = ref(null)
const newTitle = ref('')
const newDocType = ref('other')
const isDragOver = ref(false)
const uploading = ref(false)
const templateDialog = ref(false)
const templates = ref([])
const templatesLoading = ref(false)
const selectedTemplate = ref(null)
const generating = ref(false)
const history = ref([])
const historyLoading = ref(false)
let historyLoaded = false
const notes = ref([])
const notesLoading = ref(false)
const noteSaving = ref(false)
const newNoteText = ref('')
let notesLoaded = false

const previewDialog = ref(false)
const previewUrl = ref('')
const previewKind = ref('')
const previewTitle = ref('')

const taskDialog = ref(false)
const taskSaving = ref(false)
const taskForm = ref({ title: '', description: '', assigned_to: null, due_date: null, priority: 'medium' })
const lawyers = ref([])

const assignDialog = ref(false)
const assignSaving = ref(false)
const assignLawyerId = ref(null)
const assignableLawyers = computed(() => {
  const taken = new Set((caseItem.value?.assigned_lawyers_detail || []).map(l => l.id))
  return lawyers.value.filter(l => !taken.has(l.id))
})

const categoryLabel = computed(() => CASE_CATEGORIES.find(c => c.value === caseItem.value?.category)?.label || caseItem.value?.category)

const deadlineInfo = computed(() => {
  const d = caseItem.value?.key_deadline
  if (!d) return null
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const dl = new Date(d); dl.setHours(0, 0, 0, 0)
  const days = Math.round((dl - today) / 86400000)
  if (days < 0) return { type: 'error', icon: 'mdi-alert-octagon', label: `Процессуальный срок просрочен на ${-days} дн.` }
  if (days === 0) return { type: 'error', icon: 'mdi-alert', label: 'Процессуальный срок — сегодня' }
  if (days <= 7) return { type: 'warning', icon: 'mdi-alert', label: `Процессуальный срок через ${days} дн.` }
  return { type: 'info', icon: 'mdi-gavel', label: 'Ключевой процессуальный срок' }
})
const caseTasks = computed(() => tasksStore.tasks.filter(t => t.case === caseItem.value?.id))
const openTasksCount = computed(() => caseTasks.value.filter(t => t.status !== 'done' && t.status !== 'cancelled').length)
const caseInvoices = computed(() => billingStore.invoices.filter(i => i.case === caseItem.value?.id))
const totalHours = computed(() => billingStore.timeEntries.filter(e => e.case === caseItem.value?.id).reduce((sum, e) => sum + parseFloat(e.hours || 0), 0).toFixed(2))

async function fetchData() {
  loading.value = true
  try {
    // в маршруте — uuid дела; фильтры связанных сущностей работают по int-id (FK)
    caseItem.value = await casesStore.fetchCase(route.params.id)
    const caseId = caseItem.value.id
    await Promise.all([
      documentsStore.fetchDocuments(caseId),
      tasksStore.fetchTasks({ case: caseId, page_size: 100 }),
      billingStore.fetchTimeEntries({ case: caseId, page_size: 100 }),
      billingStore.fetchInvoices({ case: caseId, page_size: 50 }),
    ])
  } catch (e) {
    error('Ошибка загрузки данных')
  } finally {
    loading.value = false
  }
}

function pickedFileOf(model) {
  // v-file-input отдаёт File или File[] в зависимости от версии Vuetify
  return Array.isArray(model) ? model[0] : model
}

const pickedFile = computed(() => pickedFileOf(newFile.value))

function onFilePicked() {
  const file = pickedFileOf(newFile.value)
  if (file && !newTitle.value.trim()) newTitle.value = file.name
}

async function uploadFile(file, title, docType) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('case', caseItem.value.id)
  formData.append('title', title || file.name)
  formData.append('document_type', docType || 'other')
  await documentsStore.uploadDocument(caseItem.value.id, formData)
}

async function handleUpload() {
  const file = pickedFileOf(newFile.value)
  if (!file) return
  uploading.value = true
  try {
    await uploadFile(file, newTitle.value.trim(), newDocType.value)
    success('Документ загружен')
    docDialog.value = false
    newFile.value = null
    newTitle.value = ''
    newDocType.value = 'other'
  } catch (e) {
    error('Ошибка загрузки')
  } finally {
    uploading.value = false
  }
}

async function openTemplateDialog() {
  templateDialog.value = true
  if (templates.value.length) return
  templatesLoading.value = true
  try {
    const { data } = await api.get('/api/v1/document-templates/')
    templates.value = data.results || data
  } catch {
    error('Ошибка загрузки шаблонов')
  } finally {
    templatesLoading.value = false
  }
}

async function handleGenerate() {
  if (!selectedTemplate.value) return
  generating.value = true
  try {
    await api.post('/api/v1/documents/generate/', {
      template: selectedTemplate.value,
      case: caseItem.value.id,
    })
    await documentsStore.fetchDocuments(caseItem.value.id)
    success('Документ создан из шаблона')
    templateDialog.value = false
    selectedTemplate.value = null
  } catch (e) {
    error(e.response?.data?.detail || 'Ошибка генерации документа')
  } finally {
    generating.value = false
  }
}

async function onFileDrop(event) {
  isDragOver.value = false
  const files = Array.from(event.dataTransfer.files)
  if (!files.length) return
  uploading.value = true
  try {
    await Promise.all(files.map(f => uploadFile(f)))
    success(`Загружено файлов: ${files.length}`)
  } catch (e) {
    error('Ошибка загрузки')
  } finally {
    uploading.value = false
  }
}

function fileIcon(name) {
  const ext = name?.split('.').pop()?.toLowerCase()
  if (['pdf'].includes(ext)) return 'mdi-file-pdf-box'
  if (['doc', 'docx'].includes(ext)) return 'mdi-file-word-box'
  if (['xls', 'xlsx'].includes(ext)) return 'mdi-file-excel-box'
  if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) return 'mdi-file-image'
  return 'mdi-file-document-outline'
}

async function deleteDoc(doc) {
  const ok = await confirmDlg('Удалить документ?', doc.title)
  if (!ok) return
  try {
    await documentsStore.deleteDocument(doc.uuid)
    success('Документ удален')
  } catch (e) {
    error('Ошибка удаления')
  }
}

function isPreviewable(doc) {
  const mime = doc.mime_type || ''
  return mime === 'application/pdf' || mime.startsWith('image/')
}

async function previewDoc(doc) {
  try {
    const { data } = await api.get(`/api/v1/documents/${doc.uuid}/download/`, { responseType: 'blob' })
    // тип blob'а важен: без него iframe не отрисует PDF
    const blob = new Blob([data], { type: doc.mime_type || 'application/octet-stream' })
    releasePreview()
    previewUrl.value = URL.createObjectURL(blob)
    previewKind.value = doc.mime_type === 'application/pdf' ? 'pdf' : 'image'
    previewTitle.value = doc.title
    previewDialog.value = true
  } catch {
    error('Не удалось загрузить файл для просмотра')
  }
}

function releasePreview() {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
}

async function loadLawyers() {
  if (lawyers.value.length) return
  const { data } = await api.get('/api/v1/users/lawyers/')
  lawyers.value = data
}

async function openTaskDialog() {
  taskDialog.value = true
  try {
    await loadLawyers()
  } catch {
    error('Не удалось загрузить список юристов')
  }
}

async function createTask() {
  if (!taskForm.value.title.trim()) return
  taskSaving.value = true
  try {
    await api.post('/api/v1/tasks/', { ...taskForm.value, case: caseItem.value.id })
    success('Задача создана')
    taskDialog.value = false
    taskForm.value = { title: '', description: '', assigned_to: null, due_date: null, priority: 'medium' }
    await tasksStore.fetchTasks({ case: caseItem.value.id, page_size: 100 })
  } catch {
    error('Ошибка создания задачи')
  } finally {
    taskSaving.value = false
  }
}

async function openAssignDialog() {
  assignDialog.value = true
  try {
    await loadLawyers()
  } catch {
    error('Не удалось загрузить список юристов')
  }
}

async function refreshCase() {
  caseItem.value = await casesStore.fetchCase(route.params.id)
}

async function assignLawyer() {
  if (!assignLawyerId.value) return
  assignSaving.value = true
  try {
    await casesStore.assignLawyer(caseItem.value.uuid, assignLawyerId.value)
    await refreshCase()
    success('Юрист назначен')
    assignDialog.value = false
    assignLawyerId.value = null
  } catch {
    error('Ошибка назначения')
  } finally {
    assignSaving.value = false
  }
}

async function unassignLawyer(lawyer) {
  const ok = await confirmDlg(
    'Снять юриста с дела?',
    `${lawyer.last_name} ${lawyer.first_name} потеряет доступ к делу.`,
    { confirmText: 'Снять', confirmColor: 'warning' },
  )
  if (!ok) return
  try {
    await casesStore.removeLawyer(caseItem.value.uuid, lawyer.id)
    await refreshCase()
    success('Юрист снят с дела')
  } catch {
    error('Ошибка')
  }
}

async function deleteCase() {
  const ok = await confirmDlg(
    'Удалить дело?',
    `«${caseItem.value.title}» и все связанные задачи, документы и записи времени будут удалены безвозвратно.`,
  )
  if (!ok) return
  try {
    await api.delete(`/api/v1/cases/${caseItem.value.uuid}/`)
    success('Дело удалено')
    router.push('/cases')
  } catch (e) {
    error(e.response?.data?.detail || 'Не удалось удалить дело')
  }
}

async function toggleTask(task) {
  try {
    if (task.status === 'done') {
      await tasksStore.updateTask(task.id, { status: 'todo' })
    } else {
      await tasksStore.completeTask(task.id)
    }
    success('Статус задачи обновлен')
  } catch (e) {
    error('Ошибка обновления задачи')
  }
}

async function handleStatusChange(newStatus) {
  statusChanging.value = true
  try {
    const updated = await casesStore.changeStatus(caseItem.value.uuid, newStatus)
    caseItem.value = updated
    success('Статус дела обновлён')
  } catch {
    error('Ошибка смены статуса')
  } finally {
    statusChanging.value = false
  }
}

function taskPriorityColor(p) {
  return TASK_PRIORITIES.find(tp => tp.value === p)?.color || 'grey'
}

const ACTION_COLORS = {
  CREATE: 'success', UPDATE: 'primary', DELETE: 'error',
  STATUS_CHANGE: 'warning', ASSIGN_LAWYER: 'info',
  UPLOAD: 'teal', DOWNLOAD: 'grey',
}
function actionColor(action) { return ACTION_COLORS[action] || 'grey' }

async function loadNotes() {
  if (notesLoaded || !caseItem.value) return
  notesLoading.value = true
  try {
    const { data } = await api.get(`/api/v1/cases/${caseItem.value.id}/notes/`)
    notes.value = data.results || data
    notesLoaded = true
  } catch {
    error('Ошибка загрузки заметок')
  } finally {
    notesLoading.value = false
  }
}

async function addNote() {
  if (!newNoteText.value.trim() || !caseItem.value) return
  noteSaving.value = true
  try {
    const { data } = await api.post(`/api/v1/cases/${caseItem.value.id}/notes/`, { text: newNoteText.value.trim() })
    notes.value.unshift(data)
    newNoteText.value = ''
    success('Заметка добавлена')
  } catch {
    error('Ошибка добавления заметки')
  } finally {
    noteSaving.value = false
  }
}

async function deleteNote(id) {
  if (!caseItem.value) return
  const ok = await confirmDlg('Удалить заметку?')
  if (!ok) return
  try {
    await api.delete(`/api/v1/cases/${caseItem.value.id}/notes/${id}/`)
    notes.value = notes.value.filter(n => n.id !== id)
    success('Заметка удалена')
  } catch {
    error('Ошибка удаления заметки')
  }
}

async function loadHistory() {
  if (historyLoaded || !caseItem.value) return
  historyLoading.value = true
  try {
    const { data } = await api.get(`/api/v1/cases/${caseItem.value.uuid}/history/`)
    history.value = data.results || data
    historyLoaded = true
  } catch {
    // silent fail - history is non-critical
  } finally {
    historyLoading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.drop-zone {
  transition: border-color 0.2s, background 0.2s;
}
.drop-zone--active {
  border: 2px dashed rgb(var(--v-theme-primary)) !important;
  background: rgba(var(--v-theme-primary), 0.04) !important;
}
</style>
