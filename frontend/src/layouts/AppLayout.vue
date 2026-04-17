<template>
  <v-layout>
    <!-- Sidebar Navigation -->
    <v-navigation-drawer
      v-model="drawer"
      :rail="rail"
      permanent
      class="glass-sidebar"
      elevation="0"
    >
      <v-list-item
        nav
        class="py-6"
      >
        <template #prepend>
          <v-btn
            :icon="rail ? 'mdi-menu-open' : 'mdi-menu-open'"
            variant="text"
            :style="rail ? 'transform: rotate(180deg)' : ''"
            @click="rail = !rail"
          />
        </template>
        <v-list-item-title class="text-h5 font-weight-bold text-gradient px-2" v-if="!rail">
          Legal CRM
        </v-list-item-title>
      </v-list-item>

      <v-list density="compact" nav class="px-3">
        <v-list-item
          v-for="item in navItems"
          :key="item.to"
          :prepend-icon="item.icon"
          :title="item.title"
          :to="item.to"
          rounded="xl"
          active-class="bg-primary-lighten-4 text-primary font-weight-bold"
          class="mb-1"
        />
      </v-list>

      <template #append>
        <v-list density="compact" nav class="px-3 pb-4">
          <v-list-item
            v-if="auth.isAdmin"
            prepend-icon="mdi-account-group"
            title="Пользователи"
            to="/admin/users"
            rounded="xl"
            class="mb-1"
          />
          <v-list-item
            :prepend-icon="theme.global.name.value === 'light' ? 'mdi-weather-night' : 'mdi-weather-sunny'"
            :title="theme.global.name.value === 'light' ? 'Темная тема' : 'Светлая тема'"
            rounded="xl"
            class="mb-1"
            @click="toggleTheme"
          />
          <v-list-item
            prepend-icon="mdi-account-circle"
            title="Мой профиль"
            to="/profile"
            rounded="xl"
            class="mb-1"
          />
          <v-list-item
            prepend-icon="mdi-logout"
            title="Выйти"
            rounded="xl"
            class="mb-1"
            @click="handleLogout"
          />
          
          <v-list-item class="mt-4 pa-2 bg-surface rounded-xl border-1" v-if="!rail">
            <template #prepend>
              <v-avatar color="primary" size="36" elevation="2">
                <v-img v-if="auth.user?.avatar" :src="auth.user.avatar" />
                <span v-else class="text-white text-body-1 font-weight-bold">
                  {{ userInitials }}
                </span>
              </v-avatar>
            </template>
            <v-list-item-title class="text-body-2 font-weight-bold">
              {{ auth.user?.full_name || auth.user?.username }}
            </v-list-item-title>
            <v-list-item-subtitle class="text-caption">
              {{ auth.user?.role === 'admin' ? 'Администратор' : 'Юрист' }}
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </template>
    </v-navigation-drawer>

    <!-- Main Content -->
    <v-main class="bg-background">
      <v-container fluid class="pa-8">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </v-container>
    </v-main>

    <!-- Global Snackbar -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="snackbar.timeout"
      location="bottom right"
    >
      {{ snackbar.text }}
    </v-snackbar>

    <!-- Global Confirm Dialog -->
    <v-dialog v-model="confirmDialog.show" max-width="400">
      <v-card>
        <v-card-title>{{ confirmDialog.title }}</v-card-title>
        <v-card-text v-if="confirmDialog.message">{{ confirmDialog.message }}</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="grey" variant="text" @click="onCancel">Отмена</v-btn>
          <v-btn color="error" variant="elevated" @click="onConfirm">Удалить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-layout>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import { useAuthStore } from '@/stores/auth'
import { useNotification } from '@/composables/useNotification'
import { useConfirmDialog } from '@/composables/useConfirmDialog'

const router = useRouter()
const auth = useAuthStore()
const theme = useTheme()
const { snackbar } = useNotification()
const { dialog: confirmDialog, onConfirm, onCancel } = useConfirmDialog()

// Initialize theme from localStorage
const savedTheme = localStorage.getItem('theme')
if (savedTheme) {
  theme.global.name.value = savedTheme
}

function toggleTheme() {
  theme.global.name.value = theme.global.name.value === 'light' ? 'dark' : 'light'
  localStorage.setItem('theme', theme.global.name.value)
}

const drawer = ref(true)
const rail = ref(false)

const userInitials = computed(() => {
  const u = auth.user
  if (!u) return '?'
  if (u.first_name && u.last_name) return `${u.first_name[0]}${u.last_name[0]}`
  return u.username?.[0]?.toUpperCase() || '?'
})

const navItems = [
  { title: 'Дашборд', icon: 'mdi-view-dashboard', to: '/dashboard' },
  { title: 'Клиенты', icon: 'mdi-account-group', to: '/clients' },
  { title: 'Дела', icon: 'mdi-briefcase', to: '/cases' },
  { title: 'Задачи', icon: 'mdi-checkbox-marked-circle', to: '/tasks' },
  { title: 'Календарь', icon: 'mdi-calendar', to: '/calendar' },
  { title: 'Чат', icon: 'mdi-forum', to: '/chat' },
  { title: 'Учёт времени', icon: 'mdi-timer', to: '/billing/time' },
  { title: 'Счета', icon: 'mdi-receipt', to: '/billing/invoices' },
]

async function handleLogout() {
  await auth.logout()
  router.push({ name: 'Login' })
}
</script>
