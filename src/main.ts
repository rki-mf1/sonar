import "primevue/resources/themes/lara-light-indigo/theme.css";
import { createApp } from 'vue'
import { createPinia } from 'pinia'
//PrimeVue and Components
import PrimeVue from 'primevue/config'
import Button from 'primevue/button'
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Paginator from 'primevue/paginator'
import ProgressSpinner from 'primevue/progressspinner'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Card from 'primevue/card'
import InputSwitch from "primevue/inputswitch";
import SplitButton from "primevue/splitbutton";
import Calendar from "primevue/calendar";
import App from './App.vue';
import router from './router'

import FilterGroup from "./components/FilterGroup.vue";
import Statistics from "./components/Statistics.vue";

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(PrimeVue)
app.component('Button', Button)
app.component('InputText', InputText)
app.component('Dropdown', Dropdown)
app.component('InputNumber', InputNumber)
app.component('Paginator', Paginator)
app.component('DataTable', DataTable)
app.component('Column', Column)
app.component('Card', Card)
app.component('ProgressSpinner', ProgressSpinner)
app.component('InputSwitch', InputSwitch)
app.component('SplitButton', SplitButton)
app.component('FilterGroup', FilterGroup)
app.component('Statistics', Statistics)
app.component('Calendar', Calendar)
app.mount('#app')
