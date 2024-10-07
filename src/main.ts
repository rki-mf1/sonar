import 'primeflex/primeflex.css';
import 'primevue/resources/themes/aura-light-blue/theme.css';
import './util/custom_theme.css';
import 'primeicons/primeicons.css'; //icons

import PrimeVue from 'primevue/config'
import Menubar from "primevue/menubar";
import Button from 'primevue/button'
import RadioButton from 'primevue/radiobutton';
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import ProgressSpinner from 'primevue/progressspinner'
import DataTable from 'primevue/datatable'
import Paginator from 'primevue/paginator'
import Column from 'primevue/column'
import Card from 'primevue/card'
import InputSwitch from "primevue/inputswitch";
import SplitButton from "primevue/splitbutton";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import Dialog from "primevue/dialog";
import MultiSelect from "primevue/multiselect";
import Calendar from "primevue/calendar";
import Chart from 'primevue/chart';
import Tooltip from 'primevue/tooltip';
import Slider from 'primevue/slider';
import Accordion from 'primevue/accordion';
import AccordionTab from 'primevue/accordiontab';
import OverlayPanel from 'primevue/overlaypanel';
import Chip from 'primevue/chip';
import Message from 'primevue/message';
import { OhVueIcon, addIcons } from 'oh-vue-icons'
import { FaDna } from 'oh-vue-icons/icons'
import { FaCalendarAlt } from "oh-vue-icons/icons";
import Toast from 'primevue/toast';
addIcons(FaDna, FaCalendarAlt)

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import FilterGroup from "./components/FilterGroup.vue";
import GenomicProfileLabel from "./components/GenomicProfileLabel.vue";
import SampleDetails from "./components/SampleDetails.vue";
import Statistics from "./components/Statistics.vue";
import ExampleUsage from "./components/ExampleUsage.vue";

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.use(PrimeVue)


app.component('FilterGroup', FilterGroup)
app.component('GenomicProfileLabel', GenomicProfileLabel)
app.component('SampleDetails', SampleDetails)
app.component('Statistics', Statistics)
app.component('ExampleUsage', ExampleUsage)

app.component('IconField', IconField)
app.component('Menubar', Menubar)
app.component('InputIcon', InputIcon)
app.component('Dialog', Dialog)
app.component('MultiSelect', MultiSelect)
app.component('Button', Button)
app.component('RadioButton', RadioButton)
app.component('InputText', InputText)
app.component('Dropdown', Dropdown)
app.component('InputNumber', InputNumber)
app.component('DataTable', DataTable)
app.component('Paginator', Paginator)
app.component('Column', Column)
app.component('Card', Card)
app.component('ProgressSpinner', ProgressSpinner)
app.component('InputSwitch', InputSwitch)
app.component('SplitButton', SplitButton)
app.component('Calendar', Calendar)
app.component('Chart', Chart)
app.component('Slider', Slider)
app.component('AccordionTab', AccordionTab)
app.component('Accordion', Accordion)
app.component("v-icon", OhVueIcon);
app.component('OverlayPanel', OverlayPanel)
app.component('Chip', Chip)
app.directive('tooltip', Tooltip);
app.component('Message', Message)
app.component('Toast', Toast)

app.mount('#app')
