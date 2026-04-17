<template>
  <div>
    <page-header :title="isEdit ? 'Редактировать дело' : 'Новое дело'">
      <v-btn variant="text" prepend-icon="mdi-arrow-left" @click="$router.back()">Назад</v-btn>
    </page-header>

    <v-card max-width="900">
      <v-card-text>
        <v-form ref="formRef" @submit.prevent="handleSubmit">
          <v-row>
            <v-col cols="12" md="8">
              <v-text-field
                v-model="form.title"
                label="Название дела *"
                placeholder="Например: Представительство в суде по иску..."
                :rules="[required]"
              />
            </v-col>
            <v-col cols="12" md="4">
              <v-text-field v-model="form.case_number" label="Номер дела" hint="Оставьте пустым для автогенерации" persistent-hint />
            </v-col>
          </v-row>

          <v-row dense>
            <v-col cols="12" md="6">
              <v-autocomplete
                v-model="form.client"
                :items="clients"
                item-title="display_name"
                item-value="id"
                label="Клиент *"
                :loading="loadingClients"
                :rules="[required]"
                clearable
              />
            </v-col>
            <v-col cols="12" md="3">
              <v-select
                v-model="form.status"
                :items="CASE_STATUSES"
                item-title="label"
                item-value="value"
                label="Статус *"
                :rules="[required]"
              />
            </v-col>
            <v-col cols="12" md="3">
              <v-select
                v-model="form.category"
                :items="CASE_CATEGORIES"
                item-title="label"
                item-value="value"
                label="Категория *"
                :rules="[required]"
              />
            </v-col>
          </v-row>

          <v-row dense>
            <v-col cols="12" md="6">
              <v-select
                v-model="form.lead_lawyer"
                :items="lawyers"
                item-title="full_name"
                item-value="id"
                label="Ответственный юрист"
                :loading="loadingLawyers"
                clearable
              />
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field v-model="form.opened_at" label="Дата открытия" type="date" />
            </v-col>
          </v-row>

          <v-row dense>
            <v-col cols="12" md="6">
              <v-text-field v-model="form.court_name" label="Название суда" />
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field v-model="form.court_case_number" label="Номер дела в суде" />
            </v-col>
          </v-row>

          <v-row dense>
            <v-col cols="12" md="4">
              <v-text-field
                v-model="form.hourly_rate"
                label="Часовая ставка (руб.)"
                type="number"
                prefix="₽"
              />
            </v-col>
            <v-col cols="12" md="4">
              <v-text-field v-model="form.expected_close_date" label="Планируемая дата закрытия" type="date" />
            </v-col>
          </v-row>

          <v-textarea v-model="form.description" label="Описание / Детали дела" rows="4" />

          <v-divider class="my-4" />

          <div class="d-flex gap-2">
            <v-btn type="submit" color="primary" :loading="saving">
              {{ isEdit ? 'Сохранить изменения' : 'Создать дело' }}
            </v-btn>
            <v-btn variant="text" @click="$router.back()">Отмена</v-btn>
          </div>
        </v-form>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCasesStore } from '@/stores/cases'
import { useClientsStore } from '@/stores/clients'
import { useNotification } from '@/composables/useNotification'
import { CASE_STATUSES, CASE_CATEGORIES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import api from '@/plugins/axios'

const router = useRouter()
const route = useRoute()
const casesStore = useCasesStore()
const clientsStore = useClientsStore()
const { success, error } = useNotification()

const isEdit = computed(() => !!route.params.id)
const formRef = ref(null)
const saving = ref(false)
const loadingClients = ref(false)
const loadingLawyers = ref(false)
const required = v => !!v || 'Обязательное поле'

const clients = ref([])
const lawyers = ref([])

const form = ref({
  title: '',
  case_number: '',
  client: null,
  status: 'new',
  category: 'civil',
  lead_lawyer: null,
  court_name: '',
  court_case_number: '',
  opened_at: new Date().toISOString().substr(0, 10),
  expected_close_date: null,
  description: '',
  hourly_rate: null,
})

async function fetchInitialData() {
  loadingClients.value = true
  loadingLawyers.value = true
  try {
    const [clientsRes, lawyersRes] = await Promise.all([
      api.get('/api/v1/clients/'),
      api.get('/api/v1/users/lawyers/'),
    ])
    clients.value = clientsRes.data.results || clientsRes.data
    lawyers.value = lawyersRes.data.map(l => ({
      ...l,
      full_name: `${l.last_name} ${l.first_name}`.trim() || l.username
    }))
  } catch (e) {
    error('Ошибка загрузки данных')
  } finally {
    loadingClients.value = false
    loadingLawyers.value = false
  }
}

onMounted(async () => {
  await fetchInitialData()
  
  if (isEdit.value) {
    try {
      const caseData = await casesStore.fetchCase(route.params.id)
      Object.assign(form.value, caseData)
      // Extract ID if client is an object
      if (typeof form.value.client === 'object') {
        form.value.client = form.value.client.id
      }
      if (typeof form.value.lead_lawyer === 'object') {
        form.value.lead_lawyer = form.value.lead_lawyer.id
      }
    } catch (e) {
      error('Ошибка загрузки дела')
    }
  } else if (route.query.client) {
    form.value.client = parseInt(route.query.client)
  }
})

async function handleSubmit() {
  const { valid } = await formRef.value.validate()
  if (!valid) return
  
  saving.value = true
  try {
    if (isEdit.value) {
      await casesStore.updateCase(route.params.id, form.value)
      success('Дело обновлено')
    } else {
      const created = await casesStore.createCase(form.value)
      success('Дело создано')
      router.push(`/cases/${created.id}`)
      return
    }
    router.push(`/cases/${route.params.id}`)
  } catch (e) {
    error('Ошибка сохранения')
  } finally {
    saving.value = false
  }
}
</script>
