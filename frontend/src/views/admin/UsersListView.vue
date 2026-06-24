<template>
  <div>
    <page-header title="Пользователи" :subtitle="`Всего: ${total}`">
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openDialog()">Новый пользователь</v-btn>
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
              v-model="filterRole"
              :items="roleOptions"
              item-value="value"
              item-title="title"
              label="Роль"
              clearable
              hide-details
              @update:model-value="fetchData"
            />
          </v-col>
          <v-col cols="6" md="2">
            <v-select
              v-model="filterActive"
              :items="activeOptions"
              item-value="value"
              item-title="title"
              label="Статус"
              clearable
              hide-details
              @update:model-value="fetchData"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <v-card>
      <v-data-table
        :headers="headers"
        :items="users"
        :loading="loading"
        :search="search"
        items-per-page="25"
      >
        <template #item.full_name="{ item }">
          <div class="d-flex align-center gap-3 py-1">
            <v-avatar size="32" color="primary" variant="tonal">
              <v-img v-if="item.avatar" :src="item.avatar" />
              <span v-else class="text-caption font-weight-bold">{{ initials(item) }}</span>
            </v-avatar>
            <div>
              <div class="font-weight-medium">{{ item.full_name }}</div>
              <div class="text-caption text-medium-emphasis">{{ item.username }}</div>
            </div>
          </div>
        </template>

        <template #item.role="{ item }">
          <v-chip size="small" :color="item.role === 'admin' ? 'primary' : 'default'" variant="tonal">
            {{ item.role === 'admin' ? 'Администратор' : 'Юрист' }}
          </v-chip>
        </template>

        <template #item.is_active="{ item }">
          <v-chip size="small" :color="item.is_active ? 'success' : 'error'" variant="tonal">
            {{ item.is_active ? 'Активен' : 'Заблокирован' }}
          </v-chip>
        </template>

        <template #item.date_joined="{ item }">
          {{ formatDate(item.date_joined) }}
        </template>

        <template #item.actions="{ item }">
          <div class="d-flex gap-1 justify-end">
            <v-btn icon="mdi-pencil" size="small" variant="text" color="primary" @click="openDialog(item)" />
            <v-btn
              :icon="item.is_active ? 'mdi-account-cancel' : 'mdi-account-check'"
              size="small"
              variant="text"
              :color="item.is_active ? 'warning' : 'success'"
              :title="item.is_active ? 'Заблокировать' : 'Активировать'"
              @click="toggleActive(item)"
            />
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- User Dialog -->
    <v-dialog v-model="dialog.show" max-width="520" persistent>
      <v-card>
        <v-card-title>{{ dialog.user ? 'Редактировать пользователя' : 'Новый пользователь' }}</v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <v-form ref="formRef" @submit.prevent="handleSave">
            <v-row dense>
              <v-col cols="6">
                <v-text-field v-model="form.last_name" label="Фамилия" class="mb-2" />
              </v-col>
              <v-col cols="6">
                <v-text-field v-model="form.first_name" label="Имя" class="mb-2" />
              </v-col>
            </v-row>
            <v-text-field
              v-if="!dialog.user"
              v-model="form.username"
              label="Логин *"
              :rules="[required]"
              autocomplete="off"
              class="mb-2"
            />
            <v-text-field v-model="form.email" label="Email" type="email" class="mb-2" />
            <v-text-field v-model="form.phone" label="Телефон" class="mb-2" />
            <v-select
              v-model="form.role"
              :items="USER_ROLES"
              item-title="label"
              item-value="value"
              label="Роль"
              class="mb-2"
            />
            <v-text-field
              v-if="!dialog.user"
              v-model="form.password"
              label="Пароль *"
              type="password"
              :rules="[required, minLength8]"
              autocomplete="new-password"
              class="mb-2"
            />
          </v-form>
        </v-card-text>
        <v-divider />
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog.show = false">Отмена</v-btn>
          <v-btn color="primary" variant="tonal" :loading="saving" @click="handleSave">
            {{ dialog.user ? 'Сохранить' : 'Создать' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useNotification } from '@/composables/useNotification'
import { formatDate } from '@/utils/formatters'
import { USER_ROLES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import api from '@/plugins/axios'

const { success, error } = useNotification()

const users = ref([])
const loading = ref(false)
const search = ref('')
const filterRole = ref('')
const filterActive = ref('')
let searchTimeout = null

const formRef = ref(null)
const saving = ref(false)
const dialog = ref({ show: false, user: null })
const form = ref(emptyForm())

const required = v => !!v || 'Обязательное поле'
const minLength8 = v => (v && v.length >= 8) || 'Минимум 8 символов'

function emptyForm() {
  return { username: '', email: '', first_name: '', last_name: '', phone: '', role: 'lawyer', password: '' }
}

const total = computed(() => filteredUsers.value.length)
const filteredUsers = computed(() => {
  let list = users.value
  if (filterRole.value) list = list.filter(u => u.role === filterRole.value)
  if (filterActive.value !== '') list = list.filter(u => String(u.is_active) === filterActive.value)
  return list
})

const roleOptions = [{ value: '', title: 'Все' }, ...USER_ROLES.map(r => ({ value: r.value, title: r.label }))]
const activeOptions = [{ value: '', title: 'Все' }, { value: 'true', title: 'Активные' }, { value: 'false', title: 'Заблокированные' }]

const headers = [
  { title: 'Пользователь', key: 'full_name', sortable: true },
  { title: 'Email', key: 'email', sortable: true },
  { title: 'Телефон', key: 'phone', sortable: false },
  { title: 'Роль', key: 'role', sortable: true },
  { title: 'Статус', key: 'is_active', sortable: true },
  { title: 'Дата регистрации', key: 'date_joined', sortable: true },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

function initials(user) {
  const parts = [user.first_name?.[0], user.last_name?.[0]].filter(Boolean)
  return parts.length ? parts.join('').toUpperCase() : user.username?.[0]?.toUpperCase() || '?'
}

async function fetchData() {
  loading.value = true
  try {
    const { data } = await api.get('/api/v1/users/')
    users.value = data.results || data
  } catch {
    error('Ошибка загрузки пользователей')
  } finally {
    loading.value = false
  }
}

function debouncedFetch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(fetchData, 300)
}

function openDialog(user = null) {
  dialog.value.user = user
  form.value = user
    ? { email: user.email || '', first_name: user.first_name || '', last_name: user.last_name || '', phone: user.phone || '', role: user.role }
    : emptyForm()
  dialog.value.show = true
}

async function handleSave() {
  const { valid } = await formRef.value.validate()
  if (!valid) return
  saving.value = true
  try {
    if (dialog.value.user) {
      const { data } = await api.patch(`/api/v1/users/${dialog.value.user.id}/`, form.value)
      const idx = users.value.findIndex(u => u.id === data.id)
      if (idx !== -1) users.value[idx] = data
      success('Пользователь обновлён')
    } else {
      const { data } = await api.post('/api/v1/users/', form.value)
      users.value.unshift(data)
      success('Пользователь создан')
    }
    dialog.value.show = false
  } catch (e) {
    const msg = e.response?.data ? Object.values(e.response.data).flat().join(', ') : 'Ошибка сохранения'
    error(msg)
  } finally {
    saving.value = false
  }
}

async function toggleActive(user) {
  try {
    const { data } = await api.patch(`/api/v1/users/${user.id}/`, { is_active: !user.is_active })
    const idx = users.value.findIndex(u => u.id === data.id)
    if (idx !== -1) users.value[idx] = data
    success(data.is_active ? 'Пользователь активирован' : 'Пользователь заблокирован')
  } catch {
    error('Ошибка')
  }
}

onMounted(fetchData)
</script>
