<template>
  <div v-if="caseItem">
    <page-header :title="caseItem.title" :subtitle="caseItem.case_number">
      <template #default>
        <v-btn variant="outlined" prepend-icon="mdi-pencil" :to="`/cases/${caseItem.id}/edit`" class="mr-2">
          Редактировать
        </v-btn>
        <status-chip :value="caseItem.status" :options="CASE_STATUSES" />
      </template>
    </page-header>

    <v-tabs v-model="tab" color="primary" class="mb-4 border-b">
      <v-tab value="info">Инфо</v-tab>
      <v-tab value="documents">Документы ({{ documentsStore.documents.length }})</v-tab>
      <v-tab value="tasks">Задачи ({{ openTasksCount }})</v-tab>
      <v-tab value="billing">Биллинг</v-tab>
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
            <v-card class="mb-4" :to="`/clients/${caseItem.client}`">
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
              <v-card-title>Команда</v-card-title>
              <v-list density="compact">
                <v-list-item v-if="caseItem.lead_lawyer_detail" :title="`${caseItem.lead_lawyer_detail.last_name} ${caseItem.lead_lawyer_detail.first_name}`" subtitle="Ответственный юрист" prepend-icon="mdi-account-star" />
                <v-list-item v-for="lawyer in caseItem.assigned_lawyers_detail" :key="lawyer.id" :title="`${lawyer.last_name} ${lawyer.first_name}`" subtitle="Юрист" prepend-icon="mdi-account" />
              </v-list>
            </v-card>
          </v-col>
        </v-row>
      </v-window-item>

      <!-- Documents Tab -->
      <v-window-item value="documents">
        <v-card>
          <v-card-title class="d-flex justify-space-between align-center">
            Документы
            <v-btn color="primary" prepend-icon="mdi-upload" variant="tonal" size="small" @click="docDialog = true">Загрузить</v-btn>
          </v-card-title>
          <v-list v-if="documentsStore.documents.length">
            <v-list-item v-for="doc in documentsStore.documents" :key="doc.id" :title="doc.name" :subtitle="formatDate(doc.created_at)">
              <template #prepend>
                <v-icon icon="mdi-file-document-outline" class="mr-3" />
              </template>
              <template #append>
                <v-btn icon="mdi-download" variant="text" size="small" @click="documentsStore.downloadDocument(doc.id, doc.name)" />
                <v-btn icon="mdi-delete" variant="text" size="small" color="error" @click="deleteDoc(doc.id)" />
              </template>
            </v-list-item>
          </v-list>
          <v-card-text v-else class="text-center pa-12 text-medium-emphasis">Нет загруженных документов</v-card-text>
        </v-card>
      </v-window-item>

      <!-- Tasks Tab -->
      <v-window-item value="tasks">
        <v-card>
          <v-card-title class="d-flex justify-space-between align-center">
            Задачи
            <v-btn color="primary" prepend-icon="mdi-plus" variant="tonal" size="small" to="/tasks">Все задачи</v-btn>
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
                <v-btn color="primary" block to="/billing/time">Управлять временем</v-btn>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="6">
            <v-card>
              <v-card-title>Счета</v-card-title>
              <v-card-text v-if="caseInvoices.length">
                <v-list density="compact">
                  <v-list-item v-for="inv in caseInvoices" :key="inv.id" :title="inv.number" :subtitle="formatDate(inv.date)">
                    <template #append>
                      <v-chip size="x-small" color="success" v-if="inv.status === 'paid'">Оплачен</v-chip>
                      <v-chip size="x-small" color="primary" v-else>{{ inv.status }}</v-chip>
                    </template>
                  </v-list-item>
                </v-list>
              </v-card-text>
              <v-card-text v-else class="text-center pa-4 text-medium-emphasis">Нет выставленных счетов</v-card-text>
              <v-divider />
              <v-card-actions>
                <v-btn variant="text" block to="/billing/invoices">Перейти к счетам</v-btn>
              </v-card-actions>
            </v-card>
          </v-col>
        </v-row>
      </v-window-item>
    </v-window>

    <!-- Upload Dialog -->
    <v-dialog v-model="docDialog" max-width="500">
      <v-card>
        <v-card-title>Загрузить документ</v-card-title>
        <v-card-text>
          <v-file-input v-model="newFile" label="Выберите файл" prepend-icon="mdi-file-upload" show-size border @update:model-value="handleUpload" />
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
  <div v-else-if="loading" class="d-flex justify-center mt-12">
    <v-progress-circular indeterminate color="primary" />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useCasesStore } from '@/stores/cases'
import { useDocumentsStore } from '@/stores/documents'
import { useTasksStore } from '@/stores/tasks'
import { useBillingStore } from '@/stores/billing'
import { formatDate } from '@/utils/formatters'
import { CASE_STATUSES, CASE_CATEGORIES, TASK_STATUSES, TASK_PRIORITIES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusChip from '@/components/common/StatusChip.vue'
import { useNotification } from '@/composables/useNotification'

const route = useRoute()
const casesStore = useCasesStore()
const documentsStore = useDocumentsStore()
const tasksStore = useTasksStore()
const billingStore = useBillingStore()
const { success, error } = useNotification()

const caseItem = ref(null)
const loading = ref(true)
const tab = ref('info')
const docDialog = ref(false)
const newFile = ref(null)

const categoryLabel = computed(() => CASE_CATEGORIES.find(c => c.value === caseItem.value?.category)?.label || caseItem.value?.category)
const caseTasks = computed(() => tasksStore.tasks.filter(t => t.case === caseItem.value?.id))
const openTasksCount = computed(() => caseTasks.value.filter(t => t.status !== 'done' && t.status !== 'cancelled').length)
const caseInvoices = computed(() => billingStore.invoices.filter(i => i.case === caseItem.value?.id))
const totalHours = computed(() => billingStore.timeEntries.filter(e => e.case === caseItem.value?.id).reduce((sum, e) => sum + parseFloat(e.duration_hours), 0).toFixed(2))

async function fetchData() {
  loading.value = true
  try {
    caseItem.value = await casesStore.fetchCase(route.params.id)
    await Promise.all([
      documentsStore.fetchDocuments(route.params.id),
      tasksStore.fetchTasks({ case: route.params.id, page_size: 100 }),
      billingStore.fetchTimeEntries({ case: route.params.id, page_size: 100 }),
      billingStore.fetchInvoices({ case: route.params.id, page_size: 50 }),
    ])
  } catch (e) {
    error('Ошибка загрузки данных')
  } finally {
    loading.value = false
  }
}

async function handleUpload() {
  if (!newFile.value) return
  const formData = new FormData()
  formData.append('file', newFile.value[0])
  formData.append('case', caseItem.value.id)
  formData.append('name', newFile.value[0].name)
  try {
    await documentsStore.uploadDocument(caseItem.value.id, formData)
    success('Документ загружен')
    docDialog.value = false
    newFile.value = null
  } catch (e) {
    error('Ошибка загрузки')
  }
}

async function deleteDoc(id) {
  if (!confirm('Удалить документ?')) return
  try {
    await documentsStore.deleteDocument(id)
    success('Документ удален')
  } catch (e) {
    error('Ошибка удаления')
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

function taskPriorityColor(p) {
  return TASK_PRIORITIES.find(tp => tp.value === p)?.color || 'grey'
}

onMounted(fetchData)
</script>
