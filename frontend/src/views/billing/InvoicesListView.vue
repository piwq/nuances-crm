<template>
  <div>
    <page-header title="Счета" />
    <v-card>
      <v-card-text class="text-center pa-12">
        <v-icon icon="mdi-file-invoice-outline" size="64" color="medium-emphasis" class="mb-4" />
        <div class="text-h5 text-medium-emphasis">Страница списка счетов ещё находится в разработке</div>
        <v-btn color="primary" class="mt-6" to="/dashboard">Вернуться на дашборд</v-btn>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import PageHeader from '@/components/common/PageHeader.vue'
</script>
