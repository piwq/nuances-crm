<template>
  <div>
    <page-header title="Шаблоны документов" subtitle="Файлы .docx с плейсхолдерами {{ ... }} для генерации документов по делу">
      <v-btn color="primary" prepend-icon="mdi-plus" @click="dialog = true">Новый шаблон</v-btn>
    </page-header>

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
import { DOCUMENT_TYPES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import { useNotification } from '@/composables/useNotification'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import api from '@/plugins/axios'

const { success, error } = useNotification()
const { confirm: confirmDlg } = useConfirmDialog()

const templates = ref([])
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

onMounted(fetchData)
</script>
