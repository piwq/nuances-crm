<template>
  <div class="form-page mx-auto">
    <page-header :title="isEdit ? 'Редактировать дело' : 'Новое дело'">
      <v-btn variant="text" prepend-icon="mdi-arrow-left" @click="$router.back()">Назад</v-btn>
    </page-header>

    <v-card>
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
              <date-field v-model="form.opened_at" label="Дата открытия" />
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
            <v-col cols="12" md="8">
              <v-text-field
                v-model="form.opposing_party"
                label="Противоположная сторона"
                placeholder="ФИО или название организации"
                @blur="checkConflict"
              />
            </v-col>
            <v-col cols="12" md="4">
              <v-text-field v-model="form.opposing_party_inn" label="ИНН противоположной стороны" @blur="checkConflict" />
            </v-col>
          </v-row>

          <v-alert
            v-if="conflictHits.length"
            type="warning"
            variant="tonal"
            density="comfortable"
            icon="mdi-alert-octagon"
            class="mb-4"
          >
            <strong>Возможный конфликт интересов!</strong> Противоположная сторона совпадает с нашим клиентом:
            <div v-for="hit in conflictHits" :key="hit.uuid">
              • {{ hit.display_name }}<span v-if="hit.tax_id"> (ИНН {{ hit.tax_id }})</span>
            </div>
          </v-alert>

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
              <date-field v-model="form.expected_close_date" label="Планируемая дата закрытия" />
            </v-col>
          </v-row>

          <v-row dense>
            <v-col cols="12" md="4">
              <date-field
                v-model="form.key_deadline"
                label="Ключевой процессуальный срок" />
            </v-col>
            <v-col cols="12" md="8">
              <v-text-field
                v-model="form.key_deadline_note"
                label="Описание срока"
                placeholder="Напр.: срок исковой давности, подача апелляции"
              />
            </v-col>
          </v-row>

          <v-expansion-panels variant="accordion" class="mb-4">
            <v-expansion-panel>
              <v-expansion-panel-title>
                <v-icon size="18" class="mr-2">mdi-calculator-variant-outline</v-icon>
                Калькулятор срока
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-row dense>
                  <v-col cols="12" md="4">
                    <date-field v-model="calc.start" label="Дата события" hide-details />
                  </v-col>
                  <v-col cols="6" md="2">
                    <v-text-field v-model.number="calc.amount" label="Через" type="number" min="1" hide-details />
                  </v-col>
                  <v-col cols="6" md="3">
                    <v-select
                      v-model="calc.unit"
                      :items="[{ title: 'дней', value: 'days' }, { title: 'месяцев', value: 'months' }]"
                      label="Единица"
                      hide-details
                    />
                  </v-col>
                  <v-col cols="12" md="3" class="d-flex align-center">
                    <v-btn variant="tonal" color="primary" block :disabled="!calcResult" @click="applyCalc">
                      Подставить
                    </v-btn>
                  </v-col>
                </v-row>
                <div v-if="calcResult" class="text-body-2 mt-3">
                  Срок: <strong>{{ formatDate(calcResult.date) }}</strong>
                  <span v-if="calcResult.shifted" class="text-warning"> — перенесён с выходного на рабочий день</span>
                </div>
                <div class="text-caption text-medium-emphasis mt-1">
                  Праздничные дни не учитываются — сверьтесь с производственным календарём.
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

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
import { calcDeadline } from '@/utils/deadlines'
import { formatDate } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import api from '@/plugins/axios'
import DateField from '@/components/common/DateField.vue'

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
  opposing_party: '',
  opposing_party_inn: '',
  opened_at: new Date().toISOString().substr(0, 10),
  expected_close_date: null,
  key_deadline: null,
  key_deadline_note: '',
  description: '',
  hourly_rate: null,
})

const calc = ref({ start: new Date().toISOString().slice(0, 10), amount: 30, unit: 'days' })
const calcResult = computed(() => calcDeadline(calc.value.start, calc.value.amount, calc.value.unit))

function applyCalc() {
  if (!calcResult.value) return
  form.value.key_deadline = calcResult.value.date
}

const conflictHits = ref([])

async function checkConflict() {
  const name = (form.value.opposing_party || '').trim()
  const inn = (form.value.opposing_party_inn || '').trim()
  if (name.length < 3 && !inn) {
    conflictHits.value = []
    return
  }
  try {
    const { data } = await api.get('/api/v1/conflict-check/', { params: { name, inn } })
    conflictHits.value = data.client_matches
  } catch {
    // проверка не критична, молча пропускаем
  }
}

async function fetchInitialData() {
  loadingClients.value = true
  loadingLawyers.value = true
  try {
    const [clientsRes, lawyersRes] = await Promise.all([
      api.get('/api/v1/clients/', { params: { page_size: 100 } }),
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
      router.push(`/cases/${created.uuid}`)
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

<style scoped>
.form-page {
  max-width: 860px;
}
</style>
