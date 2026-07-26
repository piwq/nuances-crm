<template>
  <div v-if="invoice">
    <page-header :title="`Счёт ${invoice.invoice_number}`" :subtitle="invoice.case_title">
      <template #default>
        <div class="d-flex align-center gap-2">
          <status-chip :value="invoice.status" :options="INVOICE_STATUSES" />
          <v-btn
            v-if="invoice.status === 'draft'"
            variant="tonal"
            color="info"
            prepend-icon="mdi-magic-staff"
            :loading="generating"
            @click="handleGenerate"
          >
            Из записей времени
          </v-btn>
          <v-btn
            v-if="invoice.status === 'draft'"
            variant="tonal"
            color="primary"
            prepend-icon="mdi-email-send"
            @click="openEmailDialog"
          >
            Отправить на email
          </v-btn>
          <v-btn
            v-if="invoice.status === 'draft'"
            variant="tonal"
            color="blue-grey"
            prepend-icon="mdi-send"
            @click="handleMarkSent"
          >
            Отметить как отправленный
          </v-btn>
          <v-btn
            v-if="invoice.status === 'sent' || invoice.status === 'overdue'"
            variant="tonal"
            color="success"
            prepend-icon="mdi-cash-check"
            @click="paidDialog = true"
          >
            Оплачен
          </v-btn>
          <v-btn
            variant="tonal"
            prepend-icon="mdi-file-pdf-box"
            :loading="downloadingPdf"
            @click="handleDownloadPDF"
          >
            PDF
          </v-btn>
          <v-btn variant="text" prepend-icon="mdi-arrow-left" to="/billing/invoices">Назад</v-btn>
        </div>
      </template>
    </page-header>

    <v-row>
      <!-- Left: Invoice info -->
      <v-col cols="12" md="4">
        <v-card class="mb-4">
          <v-card-title>Детали</v-card-title>
          <v-card-text>
            <v-row class="mb-1">
              <v-col cols="6" class="text-caption text-medium-emphasis">Клиент</v-col>
              <v-col cols="6" class="font-weight-medium">{{ invoice.client_name }}</v-col>
            </v-row>
            <v-row class="mb-1">
              <v-col cols="6" class="text-caption text-medium-emphasis">Дело</v-col>
              <v-col cols="6">
                <router-link :to="`/cases/${invoice.case_uuid}`" class="text-primary text-decoration-none">
                  {{ invoice.case_title }}
                </router-link>
              </v-col>
            </v-row>
            <v-row class="mb-1">
              <v-col cols="6" class="text-caption text-medium-emphasis">Выставлен</v-col>
              <v-col cols="6">{{ formatDate(invoice.issue_date) }}</v-col>
            </v-row>
            <v-row class="mb-1">
              <v-col cols="6" class="text-caption text-medium-emphasis">Срок оплаты</v-col>
              <v-col cols="6">{{ formatDate(invoice.due_date) }}</v-col>
            </v-row>
            <v-row v-if="invoice.paid_date" class="mb-1">
              <v-col cols="6" class="text-caption text-medium-emphasis">Оплачен</v-col>
              <v-col cols="6">{{ formatDate(invoice.paid_date) }}</v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <v-card>
          <v-card-title>Итого</v-card-title>
          <v-card-text>
            <div class="d-flex justify-space-between mb-1">
              <span class="text-medium-emphasis">Subtotal</span>
              <span>{{ formatCurrency(invoice.subtotal) }}</span>
            </div>
            <div v-if="invoice.tax_rate" class="d-flex justify-space-between mb-1">
              <span class="text-medium-emphasis">НДС ({{ invoice.tax_rate }}%)</span>
              <span>{{ formatCurrency(invoice.tax_amount) }}</span>
            </div>
            <v-divider class="my-2" />
            <div class="d-flex justify-space-between">
              <span class="font-weight-bold text-h6">Итого</span>
              <span class="font-weight-bold text-h6 text-primary">{{ formatCurrency(invoice.total) }}</span>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Right: Items -->
      <v-col cols="12" md="8">
        <v-card>
          <v-card-title class="d-flex justify-space-between align-center">
            Позиции счёта
            <v-btn
              v-if="invoice.status === 'draft'"
              size="small"
              variant="tonal"
              prepend-icon="mdi-plus"
              @click="openItemDialog()"
            >
              Добавить
            </v-btn>
          </v-card-title>
          <v-divider />
          <v-card-text v-if="!invoice.items?.length" class="text-center text-medium-emphasis py-8">
            Нет позиций. Нажмите «Из записей времени» для автозаполнения.
          </v-card-text>
          <v-list v-else density="compact">
            <v-list-item
              v-for="item in invoice.items"
              :key="item.id"
              class="border-b"
            >
              <v-list-item-title class="text-body-2">{{ item.description }}</v-list-item-title>
              <v-list-item-subtitle class="text-caption">
                {{ item.quantity }} × {{ formatCurrency(item.unit_price) }}
              </v-list-item-subtitle>
              <template #append>
                <div class="d-flex align-center gap-2">
                  <span class="font-weight-medium">{{ formatCurrency(item.amount) }}</span>
                  <v-btn
                    v-if="invoice.status === 'draft'"
                    icon="mdi-delete"
                    size="x-small"
                    variant="text"
                    color="error"
                    @click="handleDeleteItem(item)"
                  />
                </div>
              </template>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>

    <!-- Send Email Dialog -->
    <v-dialog v-model="emailDialog" max-width="440" persistent>
      <v-card>
        <v-card-title>Отправить счёт на email</v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <v-text-field
            v-model="emailTo"
            label="Email получателя *"
            type="email"
            prepend-inner-icon="mdi-email"
            :rules="[v => !!v || 'Обязательное поле', v => /.+@.+\..+/.test(v) || 'Некорректный email']"
            hint="Счёт будет отправлен с PDF-вложением"
            persistent-hint
          />
        </v-card-text>
        <v-divider />
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="emailDialog = false">Отмена</v-btn>
          <v-btn color="primary" variant="tonal" :loading="sendingEmail" prepend-icon="mdi-send" @click="handleSendEmail">
            Отправить
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Mark Paid Dialog -->
    <v-dialog v-model="paidDialog" max-width="360">
      <v-card>
        <v-card-title>Отметить как оплаченный</v-card-title>
        <v-card-text>
          <v-text-field v-model="paidDate" label="Дата оплаты" type="date" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="paidDialog = false">Отмена</v-btn>
          <v-btn color="success" variant="tonal" :loading="marking" @click="handleMarkPaid">Подтвердить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Add Item Dialog -->
    <v-dialog v-model="itemDialog.show" max-width="440" persistent>
      <v-card>
        <v-card-title>Добавить позицию</v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <v-form ref="itemFormRef">
            <v-text-field v-model="itemForm.description" label="Описание *" :rules="[required]" class="mb-2" />
            <v-row dense>
              <v-col cols="6">
                <v-text-field v-model.number="itemForm.quantity" label="Количество *" type="number" step="0.01" :rules="[required]" class="mb-2" />
              </v-col>
              <v-col cols="6">
                <v-text-field v-model.number="itemForm.unit_price" label="Цена *" type="number" :rules="[required]" class="mb-2" />
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>
        <v-divider />
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="itemDialog.show = false">Отмена</v-btn>
          <v-btn color="primary" variant="tonal" :loading="savingItem" @click="handleSaveItem">Добавить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>

  <div v-else-if="loading" class="d-flex justify-center pa-12">
    <v-progress-circular indeterminate color="primary" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useBillingStore } from '@/stores/billing'
import { useNotification } from '@/composables/useNotification'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { formatDate, formatCurrency } from '@/utils/formatters'
import { INVOICE_STATUSES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusChip from '@/components/common/StatusChip.vue'
import api from '@/plugins/axios'

const route = useRoute()
const store = useBillingStore()
const { success, error } = useNotification()
const { confirm } = useConfirmDialog()

const invoice = ref(null)
const loading = ref(false)
const generating = ref(false)
const marking = ref(false)
const downloadingPdf = ref(false)
const paidDialog = ref(false)
const paidDate = ref(new Date().toISOString().slice(0, 10))
const emailDialog = ref(false)
const emailTo = ref('')
const sendingEmail = ref(false)

const itemFormRef = ref(null)
const savingItem = ref(false)
const itemDialog = ref({ show: false })
const itemForm = ref({ description: '', quantity: 1, unit_price: 0 })

const required = v => !!v || 'Обязательное поле'

async function load() {
  loading.value = true
  try {
    invoice.value = await store.fetchInvoice(route.params.id)
  } catch {
    error('Ошибка загрузки счёта')
  } finally {
    loading.value = false
  }
}

async function handleGenerate() {
  generating.value = true
  try {
    invoice.value = await store.generateFromEntries(invoice.value.id)
    success('Позиции добавлены из записей времени')
  } catch (e) {
    const msg = e.response?.data?.detail || 'Нет невыставленных записей времени'
    error(msg)
  } finally {
    generating.value = false
  }
}

function openEmailDialog() {
  emailTo.value = invoice.value.client_email || ''
  emailDialog.value = true
}

async function handleSendEmail() {
  if (!emailTo.value) return
  sendingEmail.value = true
  try {
    const { data } = await api.post(`/api/v1/billing/invoices/${invoice.value.id}/send-email/`, { email: emailTo.value })
    invoice.value = data
    emailDialog.value = false
    success(`Счёт отправлен на ${emailTo.value}`)
  } catch (e) {
    error(e.response?.data?.detail || 'Ошибка отправки')
  } finally {
    sendingEmail.value = false
  }
}

async function handleMarkSent() {
  try {
    invoice.value = await store.markSent(invoice.value.id)
    success('Статус изменён на «Отправлен»')
  } catch {
    error('Ошибка')
  }
}

async function handleMarkPaid() {
  marking.value = true
  try {
    invoice.value = await store.markPaid(invoice.value.id, paidDate.value)
    success('Счёт отмечен как оплаченный')
    paidDialog.value = false
  } catch {
    error('Ошибка')
  } finally {
    marking.value = false
  }
}

async function handleDownloadPDF() {
  downloadingPdf.value = true
  try {
    await store.downloadPDF(invoice.value.id, invoice.value.invoice_number)
  } catch {
    error('Ошибка генерации PDF')
  } finally {
    downloadingPdf.value = false
  }
}

function openItemDialog() {
  itemForm.value = { description: '', quantity: 1, unit_price: 0 }
  itemDialog.value.show = true
}

async function handleSaveItem() {
  const { valid } = await itemFormRef.value.validate()
  if (!valid) return
  savingItem.value = true
  try {
    await api.post('/api/v1/billing/invoice-items/', {
      ...itemForm.value,
      invoice: invoice.value.id,
      amount: itemForm.value.quantity * itemForm.value.unit_price,
    })
    await load()
    itemDialog.value.show = false
    success('Позиция добавлена')
  } catch {
    error('Ошибка добавления позиции')
  } finally {
    savingItem.value = false
  }
}

async function handleDeleteItem(item) {
  const ok = await confirm('Удалить позицию?', item.description)
  if (!ok) return
  try {
    await api.delete(`/api/v1/billing/invoice-items/${item.id}/`)
    await load()
    success('Позиция удалена')
  } catch {
    error('Ошибка удаления')
  }
}

onMounted(load)
</script>
