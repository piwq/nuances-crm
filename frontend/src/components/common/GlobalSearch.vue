<template>
  <div>
    <!-- Trigger button in sidebar -->
    <v-list-item
      prepend-icon="mdi-magnify"
      title="Поиск"
      rounded="xs"
      class="mb-1"
      @click="open"
    >
      <template #append>
        <kbd class="text-caption text-medium-emphasis">Ctrl K</kbd>
      </template>
    </v-list-item>

    <!-- Search Dialog -->
    <v-dialog v-model="show" max-width="600" :scrim="true">
      <v-card>
        <v-text-field
          ref="inputRef"
          v-model="query"
          placeholder="Поиск по клиентам, делам, задачам..."
          prepend-inner-icon="mdi-magnify"
          variant="solo"
          flat
          hide-details
          clearable
          autofocus
          class="search-input"
          @update:model-value="debouncedSearch"
          @keydown.esc="show = false"
        />
        <v-divider />

        <div class="search-results">
          <!-- Loading -->
          <div v-if="loading" class="d-flex justify-center pa-6">
            <v-progress-circular indeterminate size="24" color="primary" />
          </div>

          <!-- No query -->
          <div v-else-if="!query" class="pa-6 text-center text-medium-emphasis text-body-2">
            Введите запрос для поиска
          </div>

          <!-- No results -->
          <div v-else-if="noResults" class="pa-6 text-center text-medium-emphasis text-body-2">
            Ничего не найдено по «{{ query }}»
          </div>

          <!-- Results -->
          <template v-else>
            <!-- Clients -->
            <div v-if="results.clients.length">
              <div class="section-label">Клиенты</div>
              <v-list-item
                v-for="client in results.clients"
                :key="`c-${client.id}`"
                :title="client.display_name"
                :subtitle="client.email || client.phone || ''"
                prepend-icon="mdi-account"
                density="compact"
                @click="navigate(`/clients/${client.uuid}`)"
              />
            </div>

            <!-- Cases -->
            <div v-if="results.cases.length">
              <div class="section-label">Дела</div>
              <v-list-item
                v-for="c in results.cases"
                :key="`case-${c.id}`"
                :title="c.title"
                :subtitle="c.case_number"
                prepend-icon="mdi-briefcase-outline"
                density="compact"
                @click="navigate(`/cases/${c.uuid}`)"
              />
            </div>

            <!-- Tasks -->
            <div v-if="results.tasks.length">
              <div class="section-label">Задачи</div>
              <v-list-item
                v-for="task in results.tasks"
                :key="`t-${task.id}`"
                :title="task.title"
                :subtitle="task.case_title || ''"
                prepend-icon="mdi-checkbox-marked-circle-outline"
                density="compact"
                @click="navigate('/tasks')"
              />
            </div>

            <!-- Documents -->
            <div v-if="results.documents.length">
              <div class="section-label">Документы</div>
              <v-list-item
                v-for="doc in results.documents"
                :key="`d-${doc.id}`"
                :title="doc.title"
                :subtitle="doc.case_title || ''"
                prepend-icon="mdi-file-document-outline"
                density="compact"
                @click="openDocument(doc)"
              />
            </div>

            <!-- Invoices -->
            <div v-if="results.invoices.length">
              <div class="section-label">Счета</div>
              <v-list-item
                v-for="inv in results.invoices"
                :key="`i-${inv.id}`"
                :title="inv.invoice_number"
                :subtitle="`${inv.client_name || ''} · ${inv.total} ₽`"
                prepend-icon="mdi-receipt-text-outline"
                density="compact"
                @click="navigate(`/billing/invoices/${inv.id}`)"
              />
            </div>
          </template>
        </div>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/plugins/axios'

const router = useRouter()

const show = ref(false)
const query = ref('')
const loading = ref(false)
const results = ref(emptyResults())

function emptyResults() {
  return { clients: [], cases: [], tasks: [], documents: [], invoices: [] }
}
let searchTimeout = null

const noResults = computed(() =>
  !loading.value && query.value &&
  Object.values(results.value).every(list => !list.length)
)

function open() {
  query.value = ''
  results.value = emptyResults()
  show.value = true
}

function navigate(path) {
  show.value = false
  router.push(path)
}

function openDocument(doc) {
  // отдельной страницы документа нет — открываем дело, где он лежит
  navigate(doc.case_uuid ? `/cases/${doc.case_uuid}` : '/cases')
}

function debouncedSearch() {
  clearTimeout(searchTimeout)
  if (!query.value?.trim()) {
    results.value = emptyResults()
    return
  }
  searchTimeout = setTimeout(doSearch, 300)
}

async function doSearch() {
  if (!query.value?.trim()) return
  loading.value = true
  const q = query.value.trim()
  try {
    const params = { search: q, page_size: 5 }
    // allSettled: недоступный раздел (например, биллинг у помощника)
    // не должен обнулять всю выдачу
    const [clients, cases, tasks, documents, invoices] = await Promise.allSettled([
      api.get('/api/v1/clients/', { params }),
      api.get('/api/v1/cases/', { params }),
      api.get('/api/v1/tasks/', { params }),
      api.get('/api/v1/documents/', { params }),
      api.get('/api/v1/billing/invoices/', { params }),
    ])
    const rows = r => (r.status === 'fulfilled' ? r.value.data.results || [] : [])
    results.value = {
      clients: rows(clients),
      cases: rows(cases),
      tasks: rows(tasks),
      documents: rows(documents),
      invoices: rows(invoices),
    }
  } catch {
    // silent
  } finally {
    loading.value = false
  }
}

function onKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault()
    open()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.search-input :deep(.v-field__input) {
  font-size: 16px;
}
.search-results {
  max-height: 420px;
  overflow-y: auto;
}
.section-label {
  padding: 8px 16px 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(var(--v-theme-on-surface), 0.5);
}
kbd {
  background: rgba(var(--v-border-color), 0.12);
  border-radius: 4px;
  padding: 1px 5px;
  font-family: inherit;
}
</style>
