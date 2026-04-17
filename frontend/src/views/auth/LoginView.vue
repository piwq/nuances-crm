<template>
  <auth-layout>
    <v-card elevation="4" class="pa-2">
      <v-card-title class="text-h6 pa-6 pb-2">Вход в систему</v-card-title>
      <v-card-text>
        <v-form @submit.prevent="handleLogin">
          <v-text-field
            v-model="form.username"
            label="Логин"
            prepend-inner-icon="mdi-account"
            :rules="[v => !!v || 'Обязательное поле']"
            autocomplete="username"
            class="mb-2"
          />
          <v-text-field
            v-model="form.password"
            label="Пароль"
            type="password"
            prepend-inner-icon="mdi-lock"
            :rules="[v => !!v || 'Обязательное поле']"
            autocomplete="current-password"
            class="mb-4"
          />
          <v-alert v-if="error" type="error" variant="tonal" class="mb-4" density="compact">
            {{ error }}
          </v-alert>
          <v-btn
            type="submit"
            color="primary"
            size="large"
            block
            :loading="loading"
          >
            Войти
          </v-btn>
        </v-form>
      </v-card-text>
    </v-card>
  </auth-layout>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AuthLayout from '@/layouts/AuthLayout.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const form = ref({ username: '', password: '' })
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(form.value.username, form.value.password)
    const redirect = route.query.redirect || '/dashboard'
    router.push(redirect)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Неверный логин или пароль'
  } finally {
    loading.value = false
  }
}
</script>
