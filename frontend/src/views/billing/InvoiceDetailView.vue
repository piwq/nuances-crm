<template>
  <div>
    <page-header title="Детали счета" />
    <v-card>
      <v-card-text class="text-center pa-12">
        <v-icon icon="mdi-file-document-outline" size="64" color="medium-emphasis" class="mb-4" />
        <div class="text-h5 text-medium-emphasis">Страница деталей счета ещё находится в разработке</div>
        <v-btn color="primary" class="mt-6" to="/billing/invoices">К списку счетов</v-btn>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import PageHeader from '@/components/common/PageHeader.vue'
</script>
