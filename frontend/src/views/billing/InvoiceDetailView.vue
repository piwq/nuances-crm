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
            color="info"
            prepend-icon="mdi-cash-multiple"
            :loading="addingExpenses"
            @click="handleAddExpenses"
          >
            Из расходов
          </v-btn>
          <v-btn
            v-if="['draft', 'sent', 'overdue'].includes(invoice.status)"
            variant="tonal"
            color="primary"
            prepend-icon="mdi-email-send"
            @click="openEmailDialog"
          >
            {{ invoice.status === 'draft' ? 'Отправить на email' : 'Отправить повторно' }}
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
          <v-btn
            variant="tonal"
            prepend-icon="mdi-file-sign"
            :loading="downloadingAct"
            @click="handleDownloadAct"
          >
            Акт
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
            <template v-if="Number(invoice.paid_amount) > 0">
              <v-progress-linear
                :model-value="paidPercent"
                color="success"
                height="6"
                rounded
                class="my-3"
              />
              <div class="d-flex justify-space-between text-body-2">
                <span class="text-success">Оплачено</span>
                <span class="text-success">{{ formatCurrency(invoice.paid_amount) }}</span>
              </div>
              <div v-if="Number(invoice.balance_due) > 0" class="d-flex justify-space-between text-body-2 font-weight-medium">
                <span>Остаток</span>
                <span class="text-error">{{ formatCurrency(invoice.balance_due) }}</span>
              </div>
            </template>
          </v-card-text>
        </v-card>

        <!-- Payments -->
        <v-card class="mt-4">
          <v-card-title class="d-flex justify-space-between align-center">
            Платежи
            <v-btn
              v-if="invoice.status !== 'draft' && Number(invoice.balance_due) > 0"
              size="small"
              variant="tonal"
              prepend-icon="mdi-plus"
              @click="openPaymentDialog"
            >
              Внести
            </v-btn>
          </v-card-title>
          <v-divider />
          <v-list v-if="invoice.payments?.length" density="compact">
            <v-list-item v-for="p in invoice.payments" :key="p.id">
              <v-list-item-title class="text-body-2 font-weight-medium">
                {{ formatCurrency(p.amount) }}
              </v-list-item-title>
              <v-list-item-subtitle class="text-caption">
                {{ formatDate(p.paid_date) }} · {{ p.method_display }}<span v-if="p.note"> · {{ p.note }}</span>
              </v-list-item-subtitle>
              <template #append>
                <v-btn icon="mdi-delete-outline" size="x-small" variant="text" color="error" @click="deletePayment(p)" />
              </template>
            </v-list-item>
          </v-list>
          <v-card-text v-else class="text-medium-emphasis text-body-2">
            Платежей пока нет
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
    <form-dialog v-model="emailDialog" max-width="980">
      <v-card>
        <v-card-title>Отправить счёт на email</v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <v-row>
            <v-col cols="12" md="5">
              <v-text-field
                v-model="emailTo"
                label="Email получателя *"
                type="email"
                prepend-inner-icon="mdi-email"
                :rules="[v => !!v || 'Обязательное поле', v => /.+@.+\..+/.test(v) || 'Некорректный email']"
              />
              <v-textarea
                v-model="emailMessage"
                label="Сопроводительный текст (необязательно)"
                placeholder="Например: по вашей просьбе высылаю счёт за август."
                rows="5"
                auto-grow
                counter="500"
                maxlength="500"
              />
              <div class="text-caption text-medium-emphasis mt-2">
                <v-icon size="14" class="mr-1">mdi-paperclip</v-icon>
                PDF-версия счёта прикрепится автоматически
              </div>
            </v-col>
            <v-col cols="12" md="7">
              <div class="text-caption text-medium-emphasis mb-1">Предпросмотр письма</div>
              <div class="email-preview">
                <iframe v-if="emailPreviewHtml" :srcdoc="emailPreviewHtml" title="Предпросмотр письма" />
                <div v-else class="d-flex justify-center align-center" style="height: 100%">
                  <v-progress-circular indeterminate color="primary" size="24" />
                </div>
              </div>
            </v-col>
          </v-row>
        </v-card-text>
        <v-divider />
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="emailDialog = false">Отмена</v-btn>
          <v-btn color="primary" variant="elevated" :loading="sendingEmail" prepend-icon="mdi-send" @click="handleSendEmail">
            Отправить
          </v-btn>
        </v-card-actions>
      </v-card>
    </form-dialog>

    <!-- Payment Dialog -->
    <form-dialog v-model="paymentDialog" max-width="440">
      <v-card>
        <v-card-title>Внести платёж</v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <div class="text-body-2 text-medium-emphasis mb-3">
            Остаток к оплате: <strong>{{ formatCurrency(invoice.balance_due) }}</strong>
          </div>
          <v-text-field
            v-model.number="paymentForm.amount"
            label="Сумма *"
            type="number"
            min="0"
            :max="Number(invoice.balance_due)"
            suffix="₽"
            class="mb-2"
          />
          <date-field v-model="paymentForm.paid_date" label="Дата платежа" class="mb-2" />
          <v-select
            v-model="paymentForm.method"
            :items="PAYMENT_METHODS"
            item-title="label"
            item-value="value"
            label="Способ оплаты"
            class="mb-2"
          />
          <v-text-field v-model="paymentForm.note" label="Примечание" />
        </v-card-text>
        <v-divider />
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="paymentDialog = false">Отмена</v-btn>
          <v-btn
            color="success"
            variant="elevated"
            :loading="savingPayment"
            :disabled="!paymentForm.amount || paymentForm.amount <= 0"
            @click="savePayment"
          >
            Внести
          </v-btn>
        </v-card-actions>
      </v-card>
    </form-dialog>

    <!-- Mark Paid Dialog -->
    <v-dialog v-model="paidDialog" max-width="360">
      <v-card>
        <v-card-title>Отметить как оплаченный</v-card-title>
        <v-card-text>
          <date-field v-model="paidDate" label="Дата оплаты" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="paidDialog = false">Отмена</v-btn>
          <v-btn color="success" variant="elevated" :loading="marking" @click="handleMarkPaid">Подтвердить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Add Item Dialog -->
    <form-dialog v-model="itemDialog.show" max-width="440">
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
          <v-btn color="primary" variant="elevated" :loading="savingItem" @click="handleSaveItem">Добавить</v-btn>
        </v-card-actions>
      </v-card>
    </form-dialog>
  </div>

  <div v-else-if="loading" class="d-flex justify-center pa-12">
    <v-progress-circular indeterminate color="primary" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useBillingStore } from '@/stores/billing'
import { useNotification } from '@/composables/useNotification'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { formatDate, formatCurrency } from '@/utils/formatters'
import { INVOICE_STATUSES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusChip from '@/components/common/StatusChip.vue'
import api from '@/plugins/axios'
import FormDialog from '@/components/common/FormDialog.vue'
import DateField from '@/components/common/DateField.vue'

const route = useRoute()
const store = useBillingStore()
const { success, error } = useNotification()
const { confirm } = useConfirmDialog()

const invoice = ref(null)
const loading = ref(false)
const generating = ref(false)
const marking = ref(false)
const downloadingPdf = ref(false)
const downloadingAct = ref(false)
const addingExpenses = ref(false)
const paidDialog = ref(false)
const paidDate = ref(new Date().toISOString().slice(0, 10))
const emailDialog = ref(false)
const emailTo = ref('')
const emailMessage = ref('')
const emailPreviewHtml = ref('')
const sendingEmail = ref(false)
let previewTimer = null

const PAYMENT_METHODS = [
  { value: 'transfer', label: 'Банковский перевод' },
  { value: 'cash', label: 'Наличные' },
  { value: 'card', label: 'Карта' },
  { value: 'other', label: 'Прочее' },
]
const paymentDialog = ref(false)
const savingPayment = ref(false)
const paymentForm = ref({ amount: null, paid_date: null, method: 'transfer', note: '' })

const paidPercent = computed(() => {
  const total = Number(invoice.value?.total || 0)
  if (!total) return 0
  return Math.min(100, (Number(invoice.value.paid_amount || 0) / total) * 100)
})

function openPaymentDialog() {
  paymentForm.value = {
    amount: Number(invoice.value.balance_due),
    paid_date: new Date().toISOString().slice(0, 10),
    method: 'transfer',
    note: '',
  }
  paymentDialog.value = true
}

async function savePayment() {
  savingPayment.value = true
  try {
    await api.post('/api/v1/billing/payments/', {
      invoice: invoice.value.id,
      ...paymentForm.value,
    })
    await load()
    success('Платёж внесён')
    paymentDialog.value = false
  } catch (e) {
    const data = e.response?.data
    error(data?.amount?.[0] || data?.detail || 'Ошибка сохранения платежа')
  } finally {
    savingPayment.value = false
  }
}

async function deletePayment(payment) {
  const ok = await confirm('Удалить платёж?',
    `${formatCurrency(payment.amount)} от ${formatDate(payment.paid_date)}`)
  if (!ok) return
  try {
    await api.delete(`/api/v1/billing/payments/${payment.id}/`)
    await load()
    success('Платёж удалён')
  } catch {
    error('Ошибка удаления')
  }
}

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

async function handleAddExpenses() {
  addingExpenses.value = true
  try {
    const { data } = await api.post(`/api/v1/billing/invoices/${invoice.value.id}/add-expenses/`)
    invoice.value = data
    success('Расходы добавлены в счёт')
  } catch (e) {
    error(e.response?.data?.detail || 'Нет неперевыставленных расходов')
  } finally {
    addingExpenses.value = false
  }
}

function openEmailDialog() {
  emailTo.value = invoice.value.client_email || ''
  emailMessage.value = ''
  emailPreviewHtml.value = ''
  emailDialog.value = true
  refreshPreview()
}

async function refreshPreview() {
  try {
    const { data } = await api.get(`/api/v1/billing/invoices/${invoice.value.id}/email-preview/`, {
      params: { message: emailMessage.value },
      responseType: 'text',
    })
    emailPreviewHtml.value = data
  } catch {
    emailPreviewHtml.value = '<p style="font-family:sans-serif;color:#999;padding:16px">Не удалось загрузить предпросмотр</p>'
  }
}

// предпросмотр обновляется через полсекунды после остановки ввода
watch(emailMessage, () => {
  clearTimeout(previewTimer)
  previewTimer = setTimeout(refreshPreview, 500)
})

async function handleSendEmail() {
  if (!emailTo.value) return
  sendingEmail.value = true
  try {
    const { data } = await api.post(`/api/v1/billing/invoices/${invoice.value.id}/send-email/`, {
      email: emailTo.value,
      message: emailMessage.value,
    })
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

async function handleDownloadAct() {
  downloadingAct.value = true
  try {
    const { data } = await api.get(`/api/v1/billing/invoices/${invoice.value.id}/act/`, { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `act_${invoice.value.invoice_number}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    error('Ошибка генерации акта')
  } finally {
    downloadingAct.value = false
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

<style scoped>
.email-preview {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 6px;
  overflow: hidden;
  height: min(62vh, 600px);
  background: #f5f3ec;
}
.email-preview iframe {
  width: 100%;
  height: 100%;
  border: 0;
  /* письмо свёрстано под 600px — лёгкое уменьшение, чтобы влезало целиком */
  zoom: 0.82;
}
</style>
