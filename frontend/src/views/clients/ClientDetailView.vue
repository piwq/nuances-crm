<template>
  <div v-if="client">
    <page-header :title="client.display_name" :subtitle="client.client_type === 'individual' ? 'Физическое лицо' : 'Юридическое лицо'">
      <div class="d-flex gap-2">
        <v-btn variant="outlined" prepend-icon="mdi-pencil" :to="`/clients/${client.uuid}/edit`">Редактировать</v-btn>
        <v-btn v-if="auth.isAdmin" color="error" variant="outlined" prepend-icon="mdi-delete-outline" @click="deleteClient">
          Удалить
        </v-btn>
      </div>
    </page-header>

    <v-row>
      <!-- Client Info -->
      <v-col cols="12" md="4">
        <v-card class="mb-4">
          <v-card-title>Основная информация</v-card-title>
          <v-list density="compact">
            <v-list-item v-if="client.email" prepend-icon="mdi-email" :subtitle="client.email" title="Email" />
            <v-list-item v-if="client.phone" prepend-icon="mdi-phone" :subtitle="client.phone" title="Телефон" />
            <v-list-item v-if="client.address" prepend-icon="mdi-map-marker" :subtitle="client.address" title="Адрес" />
            <template v-if="client.client_type === 'individual'">
              <v-list-item v-if="client.passport_number" prepend-icon="mdi-card-account-details" :subtitle="client.passport_number" title="Паспорт" />
              <v-list-item v-if="client.tax_id" prepend-icon="mdi-identifier" :subtitle="client.tax_id" title="ИНН" />
            </template>
            <template v-else>
              <v-list-item v-if="client.registration_number" prepend-icon="mdi-domain" :subtitle="client.registration_number" title="ОГРН" />
              <v-list-item v-if="client.legal_address" prepend-icon="mdi-office-building" :subtitle="client.legal_address" title="Юр. адрес" />
            </template>
          </v-list>
        </v-card>

        <!-- Notes -->
        <v-card v-if="client.notes" class="mb-4">
          <v-card-title>Заметки</v-card-title>
          <v-card-text>{{ client.notes }}</v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="8">
        <!-- Contact Persons -->
        <v-card v-if="client.client_type === 'legal_entity'" class="mb-4">
          <v-card-title class="d-flex justify-space-between align-center">
            Контактные лица
            <v-btn size="small" prepend-icon="mdi-plus" color="primary" variant="tonal" @click="contactDialog = true">
              Добавить
            </v-btn>
          </v-card-title>
          <v-list v-if="client.contact_persons?.length">
            <v-list-item
              v-for="cp in client.contact_persons"
              :key="cp.id"
              :subtitle="[cp.position, cp.phone, cp.email].filter(Boolean).join(' · ')"
            >
              <template #title>
                {{ cp.last_name }} {{ cp.first_name }} {{ cp.middle_name }}
                <v-chip v-if="cp.is_primary" size="x-small" color="primary" variant="tonal" class="ml-1">Основной</v-chip>
              </template>
              <template #append>
                <v-btn icon="mdi-delete-outline" size="small" variant="text" color="error" @click="deleteContact(cp)" />
              </template>
            </v-list-item>
          </v-list>
          <v-card-text v-else class="text-medium-emphasis">Нет контактных лиц</v-card-text>
        </v-card>

        <!-- Contact Person Dialog -->
        <v-dialog v-model="contactDialog" max-width="480">
          <v-card>
            <v-card-title>Новое контактное лицо</v-card-title>
            <v-card-text>
              <v-row dense>
                <v-col cols="6"><v-text-field v-model="contactForm.last_name" label="Фамилия" /></v-col>
                <v-col cols="6"><v-text-field v-model="contactForm.first_name" label="Имя" /></v-col>
              </v-row>
              <v-text-field v-model="contactForm.middle_name" label="Отчество" />
              <v-text-field v-model="contactForm.position" label="Должность" />
              <v-row dense>
                <v-col cols="6"><v-text-field v-model="contactForm.phone" label="Телефон" /></v-col>
                <v-col cols="6"><v-text-field v-model="contactForm.email" label="Email" /></v-col>
              </v-row>
              <v-checkbox v-model="contactForm.is_primary" label="Основной контакт" hide-details />
            </v-card-text>
            <v-card-actions>
              <v-spacer />
              <v-btn variant="text" @click="contactDialog = false">Отмена</v-btn>
              <v-btn color="primary" :loading="contactSaving" :disabled="!contactForm.last_name.trim()" @click="saveContact">
                Добавить
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>

        <!-- Cases -->
        <v-card>
          <v-card-title>Дела клиента ({{ cases.length }})</v-card-title>
          <v-list v-if="cases.length">
            <v-list-item
              v-for="c in cases"
              :key="c.id"
              :to="`/cases/${c.uuid}`"
              :subtitle="`${formatDate(c.opened_at)} · ${c.category}`"
            >
              <template #title>
                <span class="font-weight-medium">{{ c.title }}</span>
                <span class="text-medium-emphasis ml-2 text-body-2">{{ c.case_number }}</span>
              </template>
              <template #append>
                <status-chip :value="c.status" :options="CASE_STATUSES" />
              </template>
            </v-list-item>
          </v-list>
          <v-card-text v-else class="text-medium-emphasis">Нет дел</v-card-text>
          <v-card-actions>
            <v-btn prepend-icon="mdi-plus" variant="text" color="primary" :to="`/cases/new?client=${client.id}`">
              Создать дело
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </div>
  <div v-else-if="loading" class="d-flex justify-center mt-12">
    <v-progress-circular indeterminate color="primary" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useClientsStore } from '@/stores/clients'
import { formatDate } from '@/utils/formatters'
import { CASE_STATUSES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusChip from '@/components/common/StatusChip.vue'
import { useNotification } from '@/composables/useNotification'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import api from '@/plugins/axios'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const store = useClientsStore()
const { success, error } = useNotification()
const { confirm: confirmDlg } = useConfirmDialog()

const client = ref(null)
const cases = ref([])
const loading = ref(true)
const contactDialog = ref(false)
const contactSaving = ref(false)
const contactForm = ref(emptyContact())

function emptyContact() {
  return { last_name: '', first_name: '', middle_name: '', position: '', phone: '', email: '', is_primary: false }
}

async function saveContact() {
  if (!contactForm.value.last_name.trim()) return
  contactSaving.value = true
  try {
    await store.createContactPerson(route.params.id, contactForm.value)
    client.value = await store.fetchClient(route.params.id)
    success('Контактное лицо добавлено')
    contactDialog.value = false
    contactForm.value = emptyContact()
  } catch {
    error('Ошибка сохранения')
  } finally {
    contactSaving.value = false
  }
}

async function deleteContact(cp) {
  const ok = await confirmDlg('Удалить контактное лицо?', `${cp.last_name} ${cp.first_name}`.trim())
  if (!ok) return
  try {
    await store.deleteContactPerson(cp.id)
    client.value = await store.fetchClient(route.params.id)
    success('Контактное лицо удалено')
  } catch {
    error('Ошибка удаления')
  }
}

async function deleteClient() {
  const ok = await confirmDlg(
    'Удалить клиента?',
    `«${client.value.display_name}» будет удалён. Клиента с делами удалить нельзя.`,
  )
  if (!ok) return
  try {
    await api.delete(`/api/v1/clients/${client.value.uuid}/`)
    success('Клиент удалён')
    router.push('/clients')
  } catch (e) {
    error(e.response?.data?.detail || 'Не удалось удалить клиента')
  }
}

onMounted(async () => {
  loading.value = true
  try {
    client.value = await store.fetchClient(route.params.id)
    const { data } = await api.get(`/api/v1/clients/${route.params.id}/cases/`)
    cases.value = data
  } finally {
    loading.value = false
  }
})
</script>
