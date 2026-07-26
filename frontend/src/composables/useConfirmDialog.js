import { ref } from 'vue'

const dialog = ref({
  show: false,
  title: '',
  message: '',
  confirmText: 'Удалить',
  confirmColor: 'error',
  resolve: null,
})

export function useConfirmDialog() {
  function confirm(title, message = '', { confirmText = 'Удалить', confirmColor = 'error' } = {}) {
    return new Promise((resolve) => {
      dialog.value = { show: true, title, message, confirmText, confirmColor, resolve }
    })
  }

  function onConfirm() {
    dialog.value.show = false
    dialog.value.resolve?.(true)
  }

  function onCancel() {
    dialog.value.show = false
    dialog.value.resolve?.(false)
  }

  return { dialog, confirm, onConfirm, onCancel }
}
