<template>
  <div v-if="client">
    <page-header :title="client.display_name" :subtitle="client.client_type === 'individual' ? 'Физическое лицо' : 'Юридическое лицо'">
      <v-btn variant="outlined" prepend-icon="mdi-pencil" :to="`/clients/${client.id}/edit`">Редактировать</v-btn>
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
            </v-list-item>
          </v-list>
          <v-card-text v-else class="text-medium-emphasis">Нет контактных лиц</v-card-text>
        </v-card>

        <!-- Cases -->
        <v-card>
          <v-card-title>Дела клиента ({{ cases.length }})</v-card-title>
          <v-list v-if="cases.length">
            <v-list-item
              v-for="c in cases"
              :key="c.id"
              :to="`/cases/${c.id}`"
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
import { useRoute } from 'vue-router'
import { useClientsStore } from '@/stores/clients'
import { formatDate } from '@/utils/formatters'
import { CASE_STATUSES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusChip from '@/components/common/StatusChip.vue'
import api from '@/plugins/axios'

const route = useRoute()
const store = useClientsStore()

const client = ref(null)
const cases = ref([])
const loading = ref(true)
const contactDialog = ref(false)

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
