<template>
  <div>
    <page-header title="Календарь">
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openDialog()">Новое событие</v-btn>
    </page-header>

    <!-- Legend -->
    <div class="d-flex flex-wrap gap-3 mb-4">
      <div v-for="t in EVENT_TYPES" :key="t.value" class="d-flex align-center gap-1">
        <span class="legend-dot" :style="{ background: typeColor(t.value) }" />
        <span class="text-caption">{{ t.label }}</span>
      </div>
    </div>

    <v-card>
      <v-card-text class="pa-2 pa-sm-4">
        <FullCalendar ref="calendarRef" :options="calendarOptions" />
      </v-card-text>
    </v-card>

    <!-- Event Dialog -->
    <form-dialog v-model="dialog.show" max-width="560">
      <v-card>
        <v-card-title>{{ dialog.event ? 'Редактировать событие' : 'Новое событие' }}</v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <v-form ref="formRef" @submit.prevent="handleSave">
            <v-text-field v-model="form.title" label="Название *" :rules="[required]" class="mb-2" />
            <v-row dense>
              <v-col cols="12" md="6">
                <v-select
                  v-model="form.event_type"
                  :items="EVENT_TYPES"
                  item-title="label"
                  item-value="value"
                  label="Тип события"
                  class="mb-2"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-autocomplete
                  v-model="form.case"
                  :items="cases"
                  item-title="title"
                  item-value="id"
                  label="Дело"
                  clearable
                  :loading="loadingCases"
                  class="mb-2"
                />
              </v-col>
            </v-row>

            <v-checkbox v-model="form.all_day" label="Весь день" density="compact" class="mb-1" hide-details />

            <v-row dense class="mt-2">
              <v-col :cols="form.all_day ? 12 : 6" :md="form.all_day ? 6 : 6">
                <date-field
                  v-model="form.start_date"
                  :label="form.all_day ? 'Дата *' : 'Начало (дата) *'"
                  :rules="[required]"
                  class="mb-2" />
              </v-col>
              <v-col v-if="!form.all_day" cols="6" md="6">
                <v-text-field v-model="form.start_time" label="Время начала" type="time" class="mb-2" />
              </v-col>
            </v-row>

            <v-row v-if="!form.all_day" dense>
              <v-col cols="6">
                <date-field v-model="form.end_date" label="Конец (дата)" class="mb-2" />
              </v-col>
              <v-col cols="6">
                <v-text-field v-model="form.end_time" label="Время конца" type="time" class="mb-2" />
              </v-col>
            </v-row>

            <v-text-field v-model="form.location" label="Место" prepend-inner-icon="mdi-map-marker-outline" class="mb-2" />
            <v-textarea v-model="form.description" label="Описание" rows="2" auto-grow class="mb-2" />
            <v-select
              v-model="form.attendees"
              :items="lawyers"
              item-title="full_name"
              item-value="id"
              label="Участники"
              multiple
              chips
              closable-chips
              :loading="loadingLawyers"
            />
          </v-form>
        </v-card-text>
        <v-divider />
        <v-card-actions>
          <v-btn v-if="dialog.event" variant="text" color="error" @click="handleDelete">Удалить</v-btn>
          <v-spacer />
          <v-btn variant="text" @click="dialog.show = false">Отмена</v-btn>
          <v-btn color="primary" variant="elevated" :loading="saving" @click="handleSave">
            {{ dialog.event ? 'Сохранить' : 'Создать' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </form-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import listPlugin from '@fullcalendar/list'
import interactionPlugin from '@fullcalendar/interaction'
import ruLocale from '@fullcalendar/core/locales/ru'
import { useDisplay } from 'vuetify'
import { useEventsStore } from '@/stores/events'
import { useNotification } from '@/composables/useNotification'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { EVENT_TYPES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import api from '@/plugins/axios'
import FormDialog from '@/components/common/FormDialog.vue'
import DateField from '@/components/common/DateField.vue'

const display = useDisplay()
const store = useEventsStore()
const { success, error } = useNotification()
const { confirm } = useConfirmDialog()

const calendarRef = ref(null)
const formRef = ref(null)
const saving = ref(false)
const dialog = ref({ show: false, event: null })
const form = ref(emptyForm())

const cases = ref([])
const lawyers = ref([])
const loadingCases = ref(false)
const loadingLawyers = ref(false)

const required = v => !!v || 'Обязательное поле'

const COLOR_MAP = {
  court_hearing: '#D32F2F',
  meeting: '#1565C0',
  deadline: '#E65100',
  other: '#616161',
}
function typeColor(type) { return COLOR_MAP[type] || '#616161' }

function emptyForm(date = null) {
  return {
    title: '',
    event_type: 'other',
    case: null,
    all_day: false,
    start_date: date || new Date().toISOString().slice(0, 10),
    start_time: '10:00',
    end_date: date || new Date().toISOString().slice(0, 10),
    end_time: '11:00',
    location: '',
    description: '',
    attendees: [],
  }
}

function toISO(date, time, allDay) {
  if (!date) return null
  if (allDay) return date
  return time ? `${date}T${time}:00` : `${date}T00:00:00`
}

function fromISO(isoStr) {
  if (!isoStr) return { date: '', time: '' }
  const d = new Date(isoStr)
  // дата и время — из локальных компонентов; toISOString() давал UTC-дату
  // и сдвигал событие на сутки назад при редактировании
  const date = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  const time = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  return { date, time }
}

async function handleEventMove(info) {
  // перетаскивание/растягивание события прямо в сетке календаря
  const ev = info.event
  const allDay = ev.allDay
  const payload = {
    all_day: allDay,
    start_datetime: allDay ? ev.startStr.slice(0, 10) : ev.start.toISOString(),
    end_datetime: ev.end ? (allDay ? ev.endStr.slice(0, 10) : ev.end.toISOString()) : null,
  }
  try {
    await store.updateEvent(Number(ev.id), payload)
    success('Событие перенесено')
  } catch {
    info.revert()
    error('Не удалось перенести событие')
  }
}

function buildPayload() {
  const start = toISO(form.value.start_date, form.value.start_time, form.value.all_day)
  const end = form.value.end_date
    ? toISO(form.value.end_date, form.value.end_time, form.value.all_day)
    : null
  return {
    title: form.value.title,
    event_type: form.value.event_type,
    case: form.value.case || null,
    all_day: form.value.all_day,
    start_datetime: start,
    end_datetime: end,
    location: form.value.location,
    description: form.value.description,
    attendees: form.value.attendees,
  }
}

async function loadFormData() {
  if (cases.value.length && lawyers.value.length) return
  loadingCases.value = true
  loadingLawyers.value = true
  try {
    const [casesRes, lawyersRes] = await Promise.all([
      api.get('/api/v1/cases/', { params: { page_size: 200 } }),
      api.get('/api/v1/users/lawyers/'),
    ])
    cases.value = casesRes.data.results || casesRes.data
    lawyers.value = lawyersRes.data.map(l => ({
      ...l,
      full_name: `${l.last_name} ${l.first_name}`.trim() || l.username,
    }))
  } catch {
    error('Ошибка загрузки данных')
  } finally {
    loadingCases.value = false
    loadingLawyers.value = false
  }
}

function openDialog(event = null, date = null) {
  dialog.value.event = event
  if (event) {
    const e = event.extendedProps
    const { date: sd, time: st } = fromISO(e.start_datetime)
    const { date: ed, time: et } = fromISO(e.end_datetime)
    form.value = {
      title: e.title,
      event_type: e.event_type,
      case: e.case || null,
      all_day: e.all_day,
      start_date: sd,
      start_time: st,
      end_date: ed,
      end_time: et,
      location: e.location || '',
      description: e.description || '',
      attendees: (e.attendees_detail || []).map(a => a.id),
    }
  } else {
    form.value = emptyForm(date)
  }
  dialog.value.show = true
  loadFormData()
}

async function handleSave() {
  const { valid } = await formRef.value.validate()
  if (!valid) return
  saving.value = true
  try {
    if (dialog.value.event) {
      await store.updateEvent(dialog.value.event.id, buildPayload())
      success('Событие обновлено')
    } else {
      await store.createEvent(buildPayload())
      success('Событие создано')
    }
    dialog.value.show = false
    calendarRef.value?.getApi()?.refetchEvents()
  } catch {
    error('Ошибка сохранения')
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  const ok = await confirm('Удалить событие?', `"${dialog.value.event.extendedProps.title}" будет удалено.`)
  if (!ok) return
  try {
    await store.deleteEvent(dialog.value.event.id)
    success('Событие удалено')
    dialog.value.show = false
    calendarRef.value?.getApi()?.refetchEvents()
  } catch {
    error('Ошибка удаления')
  }
}

const calendarOptions = {
  plugins: [dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin],
  locale: ruLocale,
  initialView: display.mobile.value ? 'listWeek' : 'dayGridMonth',
  headerToolbar: display.mobile.value
    ? { left: 'prev,next', center: 'title', right: 'listWeek,dayGridMonth' }
    : { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,listWeek' },
  buttonText: { today: 'Сегодня', month: 'Месяц', week: 'Неделя', list: 'Список' },
  height: 'auto',
  selectable: true,
  editable: true,
  eventDrop: handleEventMove,
  eventResize: handleEventMove,
  events: async (fetchInfo, successCb, failureCb) => {
    try {
      await store.fetchEvents(fetchInfo.startStr, fetchInfo.endStr)
      successCb(store.eventsForCalendar)
    } catch {
      failureCb(new Error('Ошибка загрузки событий'))
    }
  },
  dateClick: info => openDialog(null, info.dateStr),
  eventClick: info => openDialog(info.event, null),
}
</script>

<style>
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}
.fc-daygrid-event { cursor: pointer; }
.fc-list-event { cursor: pointer; }

/* FullCalendar не знает про тёмную тему Vuetify: его дефолтные переменные
   дают белую шапку дней недели и светлые фоны поверх тёмной карточки */
.v-theme--dark .fc {
  --fc-page-bg-color: transparent;
  --fc-neutral-bg-color: rgba(255, 255, 255, 0.06);
  --fc-border-color: rgba(255, 255, 255, 0.12);
  --fc-today-bg-color: rgba(168, 130, 59, 0.16);
  --fc-list-event-hover-bg-color: rgba(255, 255, 255, 0.08);
}
</style>
