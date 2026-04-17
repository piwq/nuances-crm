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
          primary: '#6366F1', // Indigo 500
          secondary: '#4F46E5', // Indigo 600
          accent: '#EC4899', // Pink 500
          error: '#EF4444',
          warning: '#F59E0B',
          info: '#3B82F6',
          success: '#10B981',
          surface: '#FFFFFF',
          background: '#F8FAFC', // Slate 50
        },
      },
      dark: {
        colors: {
          primary: '#818CF8', // Indigo 400
          secondary: '#6366F1', // Indigo 500
          accent: '#F472B6', // Pink 400
          error: '#F87171',
          warning: '#FBBF24',
          info: '#60A5FA',
          success: '#34D399',
          surface: '#1E293B', // Slate 800
          background: '#0F172A', // Slate 900
        },
      },
    },
  },
  defaults: {
    VBtn: { 
      variant: 'elevated', 
      rounded: 'xl',
      class: 'text-none font-weight-bold',
      elevation: 0,
    },
    VCard: { 
      rounded: 'xl',
      elevation: 0,
      border: '1px solid rgba(var(--v-border-color), 0.12)',
    },
    VTextField: { 
      variant: 'solo', 
      flat: true,
      rounded: 'lg',
      density: 'comfortable',
      bgColor: 'surface',
    },
    VSelect: { 
      variant: 'solo', 
      flat: true,
      rounded: 'lg',
      density: 'comfortable',
      bgColor: 'surface',
    },
    VTextarea: { 
      variant: 'solo', 
      flat: true,
      rounded: 'lg',
      density: 'comfortable',
      bgColor: 'surface',
    },
    VAutocomplete: { 
      variant: 'solo', 
      flat: true,
      rounded: 'lg',
      density: 'comfortable',
      bgColor: 'surface',
    },
  },
})
