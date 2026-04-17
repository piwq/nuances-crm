<template>
  <div>
    <page-header :title="isEdit ? 'Редактировать клиента' : 'Новый клиент'">
      <v-btn variant="text" prepend-icon="mdi-arrow-left" @click="$router.back()">Назад</v-btn>
    </page-header>

    <v-card max-width="800">
      <v-card-text>
        <v-form ref="formRef" @submit.prevent="handleSubmit">
          <!-- Client Type -->
          <v-radio-group v-model="form.client_type" inline class="mb-4" :rules="[v => !!v || 'Выберите тип']">
            <v-radio label="Физическое лицо" value="individual" />
            <v-radio label="Юридическое лицо" value="legal_entity" />
          </v-radio-group>

          <!-- Individual fields -->
          <template v-if="form.client_type === 'individual'">
            <v-row dense>
              <v-col cols="12" md="4">
                <v-text-field v-model="form.last_name" label="Фамилия *" :rules="[required]" />
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field v-model="form.first_name" label="Имя" />
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field v-model="form.middle_name" label="Отчество" />
              </v-col>
            </v-row>
            <v-row dense>
              <v-col cols="12" md="4">
                <v-text-field v-model="form.passport_number" label="Паспорт" />
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field v-model="form.tax_id" label="ИНН" />
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field v-model="form.date_of_birth" label="Дата рождения" type="date" />
              </v-col>
            </v-row>
          </template>

          <!-- Legal entity fields -->
          <template v-else-if="form.client_type === 'legal_entity'">
            <v-row dense>
              <v-col cols="12" md="6">
                <v-text-field v-model="form.company_name" label="Название компании *" :rules="[required]" />
              </v-col>
              <v-col cols="12" md="3">
                <v-text-field v-model="form.registration_number" label="ОГРН" />
              </v-col>
              <v-col cols="12" md="3">
                <v-text-field v-model="form.tax_id" label="ИНН" />
              </v-col>
            </v-row>
            <v-textarea v-model="form.legal_address" label="Юридический адрес" rows="2" />
          </template>

          <v-divider class="my-4" />

          <!-- Shared fields -->
          <v-row dense>
            <v-col cols="12" md="6">
              <v-text-field v-model="form.email" label="Email" type="email" />
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field v-model="form.phone" label="Телефон" />
            </v-col>
          </v-row>
          <v-textarea v-model="form.address" label="Адрес" rows="2" />
          <v-textarea v-model="form.notes" label="Заметки" rows="3" />

          <div class="d-flex gap-2 mt-4">
            <v-btn type="submit" color="primary" :loading="loading">
              {{ isEdit ? 'Сохранить' : 'Создать клиента' }}
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
import { useClientsStore } from '@/stores/clients'
import { useNotification } from '@/composables/useNotification'
import PageHeader from '@/components/common/PageHeader.vue'

const router = useRouter()
const route = useRoute()
const store = useClientsStore()
const { success, error } = useNotification()

const isEdit = computed(() => !!route.params.id)
const formRef = ref(null)
const loading = ref(false)
const required = v => !!v || 'Обязательное поле'

const form = ref({
  client_type: 'individual',
  first_name: '', last_name: '', middle_name: '',
  date_of_birth: '', passport_number: '', tax_id: '',
  company_name: '', registration_number: '', legal_address: '',
  email: '', phone: '', address: '', notes: '',
})

onMounted(async () => {
  if (isEdit.value) {
    const client = await store.fetchClient(route.params.id)
    Object.assign(form.value, client)
  }
})

async function handleSubmit() {
  const { valid } = await formRef.value.validate()
  if (!valid) return
  loading.value = true
  try {
    if (isEdit.value) {
      await store.updateClient(route.params.id, form.value)
      success('Клиент обновлён')
      router.push(`/clients/${route.params.id}`)
    } else {
      const created = await store.createClient(form.value)
      success('Клиент создан')
      router.push(`/clients/${created.id}`)
    }
  } catch (e) {
    const msg = e.response?.data
    error(typeof msg === 'object' ? JSON.stringify(msg) : 'Ошибка сохранения')
  } finally {
    loading.value = false
  }
}
</script>
