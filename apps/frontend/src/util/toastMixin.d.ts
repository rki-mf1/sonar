import { Toast } from 'primevue/toast';
import { ComponentCustomProperties } from 'vue';

declare module '@vue/runtime-core' {
    interface ComponentCustomProperties {
        $root: any
        $toastRef: Toast | null;
        showToastError: (message: string) => void;
    }
}
