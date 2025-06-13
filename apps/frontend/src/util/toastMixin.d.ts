import { Toast } from 'primevue/toast'
import type { ToastServiceMethods } from 'primevue/toastservice';
import { ComponentPublicInstance } from 'vue'

declare module '@vue/runtime-core' {
  interface ComponentCustomProperties {
    $root: ComponentPublicInstance
    $toastRef: Toast | null
    $toast: ToastServiceMethods;
    showToastError: (message: string) => void
  }
}
