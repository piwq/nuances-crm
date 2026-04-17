import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import { ru } from 'vuetify/locale'

export default createVuetify({
  locale: {
    locale: 'ru',
    messages: { ru },
  },
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          primary:    '#2E3C56', // ink-500
          secondary:  '#7A1E2B', // claret-500
          accent:     '#A8823B', // gilt-500
          error:      '#8A3A1E', // rust-500
          warning:    '#A8823B', // gilt-500
          info:       '#2E3C56', // ink-500
          success:    '#3F6B4C', // moss-500
          surface:    '#FFFFFF',
          background: '#FBFAF6', // parchment-50
        },
      },
      dark: {
        colors: {
          primary:    '#7585A0', // ink-300
          secondary:  '#F3DDE0', // claret-100
          accent:     '#F5E9CF', // gilt-100
          error:      '#F1DAD0', // rust-100
          warning:    '#F5E9CF', // gilt-100
          info:       '#D6DCE6', // ink-100
          success:    '#DDE8DF', // moss-100
          surface:    '#0E1729', // ink-800
          background: '#070D1B', // ink-900
        },
      },
    },
  },
  defaults: {
    VBtn: {
      variant: 'elevated',
      rounded: 'xs',
      class: 'text-none font-weight-semibold',
      elevation: 0,
    },
    VCard: {
      rounded: 'xs',
      elevation: 0,
      border: true,
    },
    VTextField: {
      variant: 'outlined',
      rounded: 'xs',
      density: 'comfortable',
    },
    VSelect: {
      variant: 'outlined',
      rounded: 'xs',
      density: 'comfortable',
    },
    VTextarea: {
      variant: 'outlined',
      rounded: 'xs',
      density: 'comfortable',
    },
    VAutocomplete: {
      variant: 'outlined',
      rounded: 'xs',
      density: 'comfortable',
    },
    VChip: {
      rounded: 'xs',
    },
    VNavigationDrawer: {
      elevation: 0,
      border: 'e',
    },
  },
})
