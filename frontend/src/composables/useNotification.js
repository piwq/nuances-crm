import { ref } from 'vue'

const snackbar = ref({ show: false, text: '', color: 'success', timeout: 3000 })

export function useNotification() {
  function notify(text, color = 'success') {
    snackbar.value = { show: true, text, color, timeout: color === 'error' ? 5000 : 3000 }
  }

  function success(text) { notify(text, 'success') }
  function error(text) { notify(text, 'error') }
  function info(text) { notify(text, 'info') }

  return { snackbar, notify, success, error, info }
}
