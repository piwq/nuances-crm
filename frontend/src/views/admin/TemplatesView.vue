<template>
  <div>
    <page-header title="Шаблоны" subtitle="Документы .docx и чек-листы типовых дел">
      <v-btn v-if="tab === 'docs'" color="primary" prepend-icon="mdi-plus" @click="dialog = true">
        Новый шаблон
      </v-btn>
      <v-btn v-else color="primary" prepend-icon="mdi-plus" @click="openChecklist()">
        Новый чек-лист
      </v-btn>
    </page-header>

    <v-tabs v-model="tab" color="primary" class="mb-4 border-b">
      <v-tab value="docs">Документы</v-tab>
      <v-tab value="checklists">Чек-листы дел</v-tab>
    </v-tabs>

    <v-window v-model="tab">
    <v-window-item value="docs">

    <v-card>
      <v-data-table
        :headers="headers"
        :items="templates"
        :loading="loading"
        :items-per-page="25"
      >
        <template #item.document_type="{ item }">
          {{ item.document_type_display }}
        </template>
        <template #item.created_at="{ item }">
          {{ formatDate(item.created_at) }}
        </template>
        <template #item.actions="{ item }">
          <v-btn icon="mdi-delete-outline" size="small" variant="text" color="error" @click="deleteTemplate(item)" />
        </template>
        <template #no-data>
          <div class="text-medium-emphasis pa-8">
            Шаблонов пока нет. Доступные подстановки в .docx: {{ placeholders }}
          </div>
        </template>
      </v-data-table>
    </v-card>

    </v-window-item>

    <v-window-item value="checklists">
      <v-card>
        <v-list v-if="checklists.length">
          <v-list-item v-for="c in checklists" :key="c.id">
            <v-list-item-title class="font-weight-medium">
              {{ c.name }}
              <v-chip v-if="c.category" size="x-small" variant="tonal" class="ml-1">
                {{ categoryLabel(c.category) }}
              </v-chip>
              <v-chip v-if="!c.is_active" size="x-small" color="grey" variant="tonal" class="ml-1">
                выключен
              </v-chip>
            </v-list-item-title>
            <v-list-item-subtitle class="text-caption">
              {{ c.items.length }} задач: {{ c.items.map(i => i.title).join(' → ') }}
            </v-list-item-subtitle>
            <template #append>
              <v-btn icon="mdi-pencil" size="x-small" variant="text" @click="openChecklist(c)" />
              <v-btn icon="mdi-delete-outline" size="x-small" variant="text" color="error"
                     @click="deleteChecklist(c)" />
            </template>
          </v-list-item>
        </v-list>
        <v-card-text v-else class="text-medium-emphasis">
          Чек-листов нет. Заведите типовой набор задач — например, «исковое производство»:
          подготовить иск, оплатить пошлину, подать в суд. В карточке дела он развернётся
          в задачи со сроками одним нажатием.
        </v-card-text>
      </v-card>
    </v-window-item>
    </v-window>

    <!-- Checklist Dialog -->
    <form-dialog v-model="checklistDialog" max-width="640">
      <v-card>
        <v-card-title>{{ checklistForm.id ? 'Изменить чек-лист' : 'Новый чек-лист' }}</v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <v-row dense>
            <v-col cols="12" md="7">
              <v-text-field v-model="checklistForm.name" label="Название *" />
            </v-col>
            <v-col cols="12" md="5">
              <v-select
                v-model="checklistForm.category"
                :items="[{ label: 'Любая категория', value: '' }, ...CASE_CATEGORIES]"
                item-title="label"
                item-value="value"
                label="Категория дел"
              />
            </v-col>
          </v-row>
          <v-divider class="my-3" />
          <div class="text-body-2 font-weight-medium mb-2">Задачи</div>
          <v-row v-for="(item, i) in checklistForm.items" :key="i" dense class="align-center">
            <v-col cols="12" md="6">
              <v-text-field v-model="item.title" label="Задача" density="compact" hide-details />
            </v-col>
            <v-col cols="5" md="3">
              <v-text-field v-model.number="item.days_offset" label="Через дней" type="number"
                            density="compact" hide-details />
            </v-col>
            <v-col cols="5" md="2">
              <v-select v-model="item.priority" :items="TASK_PRIORITIES" item-title="label"
                        item-value="value" label="Приоритет" density="compact" hide-details />
            </v-col>
            <v-col cols="2" md="1">
              <v-btn icon="mdi-close" size="x-small" variant="text" @click="checklistForm.items.splice(i, 1)" />
            </v-col>
          </v-row>
          <v-btn size="small" variant="text" prepend-icon="mdi-plus" class="mt-2" @click="addChecklistItem">
            Добавить задачу
          </v-btn>
          <v-checkbox v-model="checklistForm.is_active" label="Активен" density="compact" hide-details class="mt-2" />
        </v-card-text>
        <v-divider />
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="checklistDialog = false">Отмена</v-btn>
          <v-btn color="primary" variant="elevated" :loading="savingChecklist"
                 :disabled="!checklistForm.name?.trim() || !checklistForm.items.length"
                 @click="saveChecklist">
            Сохранить
          </v-btn>
        </v-card-actions>
      </v-card>
    </form-dialog>

    <v-dialog v-model="dialog" max-width="500">
      <v-card>
        <v-card-title>Новый шаблон</v-card-title>
        <v-card-text>
          <v-text-field v-model="form.name" label="Название" />
          <v-select v-model="form.document_type" :items="DOCUMENT_TYPES" item-title="label" item-value="value" label="Тип документа" />
          <v-file-input v-model="form.file" label="Файл .docx" accept=".docx" prepend-icon="mdi-file-word" show-size />
          <v-textarea v-model="form.description" label="Описание" rows="2" auto-grow />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">Отмена</v-btn>
          <v-btn color="primary" :loading="saving" :disabled="!form.name.trim() || !pickedFile" @click="save">Загрузить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { formatDate } from '@/utils/formatters'
import { DOCUMENT_TYPES, CASE_CATEGORIES, TASK_PRIORITIES } from '@/utils/constants'
import FormDialog from '@/components/common/FormDialog.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { useNotification } from '@/composables/useNotification'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import api from '@/plugins/axios'

const { success, error } = useNotification()
const { confirm: confirmDlg } = useConfirmDialog()

const tab = ref('docs')
const templates = ref([])
const checklists = ref([])
const checklistDialog = ref(false)
const savingChecklist = ref(false)
const checklistForm = ref(emptyChecklist())

function emptyChecklist() {
  return { id: null, name: '', category: '', is_active: true, items: [] }
}

function categoryLabel(value) {
  return CASE_CATEGORIES.find(c => c.value === value)?.label || value
}

function addChecklistItem() {
  checklistForm.value.items.push({ title: '', days_offset: 0, priority: 'medium' })
}

function openChecklist(checklist = null) {
  checklistForm.value = checklist
    ? JSON.parse(JSON.stringify(checklist))
    : { ...emptyChecklist(), items: [{ title: '', days_offset: 0, priority: 'medium' }] }
  checklistDialog.value = true
}

async function loadChecklists() {
  try {
    const { data } = await api.get('/api/v1/checklists/', { params: { page_size: 100 } })
    checklists.value = data.results || data
  } catch {
    error('Ошибка загрузки чек-листов')
  }
}

async function saveChecklist() {
  savingChecklist.value = true
  const payload = {
    name: checklistForm.value.name.trim(),
    category: checklistForm.value.category || '',
    is_active: checklistForm.value.is_active,
    items: checklistForm.value.items.filter(i => i.title?.trim()),
  }
  try {
    if (checklistForm.value.id) {
      await api.patch(`/api/v1/checklists/${checklistForm.value.id}/`, payload)
    } else {
      await api.post('/api/v1/checklists/', payload)
    }
    await loadChecklists()
    success('Чек-лист сохранён')
    checklistDialog.value = false
  } catch {
    error('Ошибка сохранения чек-листа')
  } finally {
    savingChecklist.value = false
  }
}

async function deleteChecklist(checklist) {
  const ok = await confirmDlg('Удалить чек-лист?', checklist.name)
  if (!ok) return
  try {
    await api.delete(`/api/v1/checklists/${checklist.id}/`)
    await loadChecklists()
    success('Чек-лист удалён')
  } catch {
    error('Ошибка удаления')
  }
}
const loading = ref(false)
const dialog = ref(false)
const saving = ref(false)
const form = ref({ name: '', document_type: 'other', file: null, description: '' })

const pickedFile = computed(() => Array.isArray(form.value.file) ? form.value.file[0] : form.value.file)

const placeholders = ['case_number', 'case_title', 'client_name', 'client_inn', 'client_address', 'court_name', 'lead_lawyer', 'today']
  .map(p => `{{ ${p} }}`).join(', ')

const headers = [
  { title: 'Название', key: 'name', sortable: true },
  { title: 'Тип', key: 'document_type', sortable: true },
  { title: 'Описание', key: 'description', sortable: false },
  { title: 'Создан', key: 'created_at', sortable: true },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

async function fetchData() {
  loading.value = true
  try {
    const { data } = await api.get('/api/v1/document-templates/', { params: { page_size: 100 } })
    templates.value = data.results || data
  } catch {
    error('Ошибка загрузки шаблонов')
  } finally {
    loading.value = false
  }
}

async function save() {
  const file = pickedFile.value
  if (!file || !form.value.name.trim()) return
  saving.value = true
  try {
    const fd = new FormData()
    fd.append('name', form.value.name.trim())
    fd.append('document_type', form.value.document_type)
    fd.append('file', file)
    fd.append('description', form.value.description || '')
    await api.post('/api/v1/document-templates/', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    success('Шаблон загружен')
    dialog.value = false
    form.value = { name: '', document_type: 'other', file: null, description: '' }
    fetchData()
  } catch {
    error('Ошибка загрузки шаблона')
  } finally {
    saving.value = false
  }
}

async function deleteTemplate(item) {
  const ok = await confirmDlg('Удалить шаблон?', item.name)
  if (!ok) return
  try {
    await api.delete(`/api/v1/document-templates/${item.id}/`)
    templates.value = templates.value.filter(t => t.id !== item.id)
    success('Шаблон удалён')
  } catch {
    error('Ошибка удаления')
  }
}

onMounted(() => {
  fetchData()
  loadChecklists()
})
</script>
