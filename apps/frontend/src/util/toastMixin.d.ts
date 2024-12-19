import { Toast } from 'primevue/toast'
import { ComponentPublicInstance } from 'vue';

declare module '@vue/runtime-core' {
  interface ComponentCustomProperties {
    $root: ComponentPublicInstance
    $toastRef: Toast | null
    showToastError: (message: string) => void
  }
}
