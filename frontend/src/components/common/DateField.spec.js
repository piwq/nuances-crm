import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import DateField from './DateField.vue'

const vuetify = createVuetify({ components, directives })

function mountField(modelValue = null) {
  return mount(DateField, {
    props: { modelValue, label: 'Срок' },
    global: { plugins: [vuetify] },
  })
}

describe('DateField', () => {
  it('показывает ISO-дату в формате дд.мм.гггг', () => {
    // нативный input[type=date] показывал MM/DD/YYYY на английской локали браузера
    expect(mountField('2026-08-01').find('input').element.value).toBe('01.08.2026')
  })

  it('пустое значение — пустое поле', () => {
    expect(mountField(null).find('input').element.value).toBe('')
  })

  it('битое значение не роняет компонент', () => {
    expect(mountField('не дата').find('input').element.value).toBe('')
  })

  it('наружу отдаёт ISO YYYY-MM-DD', async () => {
    const wrapper = mountField('2026-08-01')
    wrapper.vm.pick(new Date(2026, 11, 31))
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['2026-12-31'])
  })

  it('поле только для чтения — дату выбирают в календаре', () => {
    expect(mountField().find('input').attributes('readonly')).toBeDefined()
  })
})
