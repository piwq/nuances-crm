<template>
  <v-row>
    <v-col cols="12" md="4">
      <v-card class="text-center pa-6">
        <v-avatar size="150" color="primary" class="mb-4">
          <v-img v-if="auth.user?.avatar" :src="auth.user.avatar" alt="Avatar" cover />
          <span v-else class="text-h2 text-white">{{ userInitials }}</span>
        </v-avatar>
        <v-file-input
          v-model="avatarFile"
          label="Сменить аватар"
          accept="image/*"
          prepend-icon="mdi-camera"
          hide-details
          variant="underlined"
          density="compact"
          @update:model-value="handleAvatarUpload"
        />
        <div class="mt-4">
          <h2 class="text-h5 font-weight-bold">{{ auth.user?.full_name }}</h2>
          <p class="text-subtitle-1 text-medium-emphasis">@{{ auth.user?.username }}</p>
          <v-chip color="primary" class="mt-2">{{ auth.user?.role === 'admin' ? 'Администратор' : 'Юрист' }}</v-chip>
        </div>
      </v-card>
    </v-col>

    <v-col cols="12" md="8">
      <v-card class="pa-6">
        <v-tabs v-model="activeTab" color="primary">
          <v-tab value="profile">Данные профиля</v-tab>
          <v-tab value="security">Безопасность</v-tab>
        </v-tabs>

        <v-window v-model="activeTab" class="mt-6">
          <v-window-item value="profile">
            <v-form ref="profileFormRef" @submit.prevent="handleUpdateProfile">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="profileForm.first_name"
                    label="Имя"
                    :rules="nameRules"
                    @keypress="allowLettersOnly"
                    required
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="profileForm.last_name"
                    label="Фамилия"
                    :rules="nameRules"
                    @keypress="allowLettersOnly"
                    required
                  />
                </v-col>
                <v-col cols="12">
                  <v-text-field
                    v-model="profileForm.email"
                    label="Email"
                    type="email"
                    :rules="emailRules"
                    required
                  />
                </v-col>
                <v-col cols="12">
                  <v-text-field
                    v-model="profileForm.phone"
                    label="Телефон"
                    placeholder="+7 (999) 999-99-99"
                    :rules="phoneRules"
                    @input="formatPhone"
                    @keypress="allowPhoneKeys"
                  />
                </v-col>
                <v-col cols="12">
                  <div class="d-flex align-center gap-3 flex-wrap">
                    <v-btn
                      color="primary"
                      variant="tonal"
                      prepend-icon="mdi-send"
                      :loading="tgLinking"
                      @click="linkTelegram"
                    >
                      Привязать Telegram
                    </v-btn>
                    <span v-if="profileForm.telegram_chat_id" class="text-body-2 text-success">
                      <v-icon size="16" class="mr-1">mdi-check-circle</v-icon>Telegram привязан
                    </span>
                    <span v-else class="text-body-2 text-medium-emphasis">
                      Уведомления о дедлайнах и задачах будут приходить в Telegram
                    </span>
                    <v-btn
                      v-if="profileForm.telegram_chat_id"
                      variant="text"
                      size="small"
                      @click="unlinkTelegram"
                    >
                      Отвязать
                    </v-btn>
                  </div>
                </v-col>

                <v-col cols="12">
                  <v-divider class="mb-4" />
                  <div class="d-flex align-center gap-3 flex-wrap mb-2">
                    <v-btn
                      color="primary"
                      variant="tonal"
                      prepend-icon="mdi-calendar-sync"
                      :loading="calendarLoading"
                      @click="getCalendarLink"
                    >
                      {{ calendarUrl ? 'Перевыпустить ссылку' : 'Подписка на календарь' }}
                    </v-btn>
                    <span class="text-body-2 text-medium-emphasis">
                      Заседания, сроки и задачи в вашем телефоне
                    </span>
                    <v-btn v-if="calendarUrl" variant="text" size="small" @click="revokeCalendar">
                      Отключить
                    </v-btn>
                  </div>
                  <v-alert v-if="calendarUrl" type="info" variant="tonal" density="comfortable">
                    <div class="text-body-2 mb-2">
                      Добавьте эту ссылку в календарь телефона
                      («Другие календари» → «Подписаться по URL»). Ссылка секретная — не пересылайте её.
                    </div>
                    <v-text-field
                      :model-value="calendarUrl"
                      readonly
                      density="compact"
                      hide-details
                      variant="outlined"
                      append-inner-icon="mdi-content-copy"
                      @click:append-inner="copyCalendarUrl"
                    />
                  </v-alert>
                </v-col>
              </v-row>
              <div class="d-flex justify-end mt-4">
                <v-btn type="submit" color="primary" :loading="loading">Сохранить</v-btn>
              </div>
            </v-form>
          </v-window-item>

          <v-window-item value="security">
            <v-form ref="passwordFormRef" @submit.prevent="handleChangePassword">
              <v-text-field
                v-model="passwordForm.current_password"
                label="Текущий пароль"
                type="password"
                :rules="[required]"
                autocomplete="current-password"
                class="mb-2"
              />
              <v-text-field
                v-model="passwordForm.new_password"
                label="Новый пароль"
                type="password"
                :rules="[required, minLength8]"
                autocomplete="new-password"
                class="mb-2"
              />
              <v-text-field
                v-model="passwordForm.confirm_password"
                label="Повторите новый пароль"
                type="password"
                :rules="[required, passwordsMatch]"
                autocomplete="new-password"
                class="mb-4"
              />
              <div class="d-flex justify-end">
                <v-btn type="submit" color="primary" :loading="passwordLoading">Изменить пароль</v-btn>
              </div>
            </v-form>
          </v-window-item>
        </v-window>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useNotification } from '@/composables/useNotification'
import api from '@/plugins/axios'

const auth = useAuthStore()
const { notify: showNotification } = useNotification()

const activeTab = ref('profile')
const loading = ref(false)
const passwordLoading = ref(false)
const tgLinking = ref(false)
const calendarLoading = ref(false)
const calendarUrl = ref('')
const avatarFile = ref(null)
const profileFormRef = ref(null)
const passwordFormRef = ref(null)

const passwordForm = ref({ current_password: '', new_password: '', confirm_password: '' })

const required = v => !!v || 'Обязательное поле'
const minLength8 = v => (v && v.length >= 8) || 'Минимум 8 символов'
const passwordsMatch = v => v === passwordForm.value.new_password || 'Пароли не совпадают'

// Validation rules
const nameRules = [
  v => !!v || 'Обязательное поле',
  v => /^[а-яёА-ЯЁa-zA-Z\-]+$/.test(v) || 'Только буквы и дефис',
]

const emailRules = [
  v => !!v || 'Обязательное поле',
  v => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) || 'Некорректный email',
]

const phoneRules = [
  v => !v || /^\+7 \(\d{3}\) \d{3}-\d{2}-\d{2}$/.test(v) || 'Формат: +7 (999) 999-99-99',
]

// Allow only Cyrillic/Latin letters and hyphen
function allowLettersOnly(e) {
  if (!/[а-яёА-ЯЁa-zA-Z\-]/.test(e.key)) e.preventDefault()
}

// Allow only digits and + for phone
function allowPhoneKeys(e) {
  if (!/[\d+]/.test(e.key)) e.preventDefault()
}

// Auto-format phone as +7 (999) 999-99-99
function formatPhone(e) {
  let digits = profileForm.value.phone.replace(/\D/g, '')
  if (digits.startsWith('8')) digits = '7' + digits.slice(1)
  if (digits.startsWith('7')) digits = digits.slice(1)
  digits = digits.slice(0, 10)

  let result = ''
  if (digits.length > 0) result = '+7 (' + digits.slice(0, 3)
  if (digits.length >= 3) result += ') ' + digits.slice(3, 6)
  if (digits.length >= 6) result += '-' + digits.slice(6, 8)
  if (digits.length >= 8) result += '-' + digits.slice(8, 10)

  profileForm.value.phone = result
}

const profileForm = ref({
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  telegram_chat_id: ''
})

const userInitials = computed(() => {
  const u = auth.user
  if (!u) return '?'
  if (u.first_name && u.last_name) return `${u.first_name[0]}${u.last_name[0]}`
  return u.username?.[0]?.toUpperCase() || '?'
})

onMounted(() => {
  if (auth.user) {
    profileForm.value = {
      first_name: auth.user.first_name || '',
      last_name: auth.user.last_name || '',
      email: auth.user.email || '',
      phone: auth.user.phone || '',
      telegram_chat_id: auth.user.telegram_chat_id || ''
    }
  }
  loadCalendarLink()
})

async function handleUpdateProfile() {
  const { valid } = await profileFormRef.value.validate()
  if (!valid) return
  loading.value = true
  try {
    const response = await api.patch('/api/v1/auth/me/', profileForm.value)
    auth.user = response.data
    showNotification('Профиль успешно обновлен', 'success')
  } catch (error) {
    showNotification('Ошибка при обновлении профиля', 'error')
  } finally {
    loading.value = false
  }
}

async function loadCalendarLink() {
  try {
    const { data } = await api.get('/api/v1/auth/calendar-link/')
    calendarUrl.value = data.url
  } catch {
    calendarUrl.value = ''  // подписки ещё нет
  }
}

async function getCalendarLink() {
  calendarLoading.value = true
  try {
    const { data } = await api.post('/api/v1/auth/calendar-link/',
      calendarUrl.value ? { regenerate: true } : {})
    calendarUrl.value = data.url
    showNotification(calendarUrl.value ? 'Ссылка готова' : 'Ссылка создана', 'success')
  } catch {
    showNotification('Не удалось получить ссылку', 'error')
  } finally {
    calendarLoading.value = false
  }
}

async function revokeCalendar() {
  try {
    await api.delete('/api/v1/auth/calendar-link/')
    calendarUrl.value = ''
    showNotification('Подписка отключена', 'success')
  } catch {
    showNotification('Ошибка', 'error')
  }
}

async function copyCalendarUrl() {
  try {
    await navigator.clipboard.writeText(calendarUrl.value)
    showNotification('Ссылка скопирована', 'success')
  } catch {
    showNotification('Скопируйте ссылку вручную', 'info')
  }
}

async function linkTelegram() {
  tgLinking.value = true
  try {
    const { data } = await api.post('/api/v1/auth/telegram-link/')
    window.open(data.link, '_blank')
    showNotification('Откройте Telegram и нажмите «Start» у бота', 'info')
  } catch (e) {
    showNotification(e.response?.data?.detail || 'Не удалось создать ссылку привязки', 'error')
  } finally {
    tgLinking.value = false
  }
}

async function unlinkTelegram() {
  try {
    const response = await api.patch('/api/v1/auth/me/', { telegram_chat_id: '' })
    auth.user = response.data
    profileForm.value.telegram_chat_id = ''
    showNotification('Telegram отвязан', 'success')
  } catch {
    showNotification('Ошибка', 'error')
  }
}

async function handleChangePassword() {
  const { valid } = await passwordFormRef.value.validate()
  if (!valid) return
  passwordLoading.value = true
  try {
    await api.post('/api/v1/auth/change-password/', {
      current_password: passwordForm.value.current_password,
      new_password: passwordForm.value.new_password,
    })
    showNotification('Пароль успешно изменён', 'success')
    passwordForm.value = { current_password: '', new_password: '', confirm_password: '' }
    passwordFormRef.value.reset()
  } catch (e) {
    const msg = e.response?.data?.detail || 'Ошибка смены пароля'
    showNotification(msg, 'error')
  } finally {
    passwordLoading.value = false
  }
}

async function handleAvatarUpload() {
  if (!avatarFile.value || avatarFile.value.length === 0) return

  const file = Array.isArray(avatarFile.value) ? avatarFile.value[0] : avatarFile.value
  const formData = new FormData()
  formData.append('avatar', file)

  loading.value = true
  try {
    const response = await api.patch('/api/v1/auth/me/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    auth.user = response.data
    showNotification('Аватар обновлен', 'success')
    avatarFile.value = null
  } catch (error) {
    showNotification('Ошибка при загрузке аватара', 'error')
  } finally {
    loading.value = false
  }
}
</script>
