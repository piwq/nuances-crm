import { ref } from 'vue'

const dialog = ref({
  show: false,
  title: '',
  message: '',
  resolve: null,
})

export function useConfirmDialog() {
  function confirm(title, message = '') {
    return new Promise((resolve) => {
      dialog.value = { show: true, title, message, resolve }
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
