import 'primeflex/primeflex.css'
import 'primevue/resources/themes/aura-light-blue/theme.css'
import './util/custom_theme.css'
import 'primevue/resources/primevue.min.css' // Core CSS
import 'primeicons/primeicons.css' //icons
import ToastMixin from './util/toastMixin'

import PrimeVue from 'primevue/config'
import Menubar from 'primevue/menubar'
import Button from 'primevue/button'
import RadioButton from 'primevue/radiobutton'
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import ProgressSpinner from 'primevue/progressspinner'
import ProgressBar from 'primevue/progressbar'
import DataTable from 'primevue/datatable'
import Paginator from 'primevue/paginator'
import Column from 'primevue/column'
import Card from 'primevue/card'
import InputSwitch from 'primevue/inputswitch'
import SplitButton from 'primevue/splitbutton'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Dialog from 'primevue/dialog'
import MultiSelect from 'primevue/multiselect'
import Calendar from 'primevue/calendar'
import Chart from 'primevue/chart'
import Tooltip from 'primevue/tooltip'
import Accordion from 'primevue/accordion'
import AccordionTab from 'primevue/accordiontab'
import OverlayPanel from 'primevue/overlaypanel'
import Chip from 'primevue/chip'
import Message from 'primevue/message'
import { OhVueIcon, addIcons } from 'oh-vue-icons'
import { FaDna } from 'oh-vue-icons/icons'
import { FaCalendarAlt } from 'oh-vue-icons/icons'
import { GiRadarSweep } from 'oh-vue-icons/icons'
import Toast from 'primevue/toast'
import ToastService from 'primevue/toastservice'
import AnimateOnScroll from 'primevue/animateonscroll'
import Panel from 'primevue/panel'
import Skeleton from 'primevue/skeleton'
import Splitter from 'primevue/splitter'
import SplitterPanel from 'primevue/splitterpanel'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Menu from 'primevue/menu'
addIcons(FaDna, FaCalendarAlt, GiRadarSweep)

// Import the chartjs plugin
import { Chart as ChartJS } from 'chart.js/auto' // Ensure you're importing Chart.js
import zoomPlugin from 'chartjs-plugin-zoom'

ChartJS.register(zoomPlugin)

import 'chartjs-adapter-moment'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import FilterGroup from './components/FilterGroup.vue'
import FilterBar from './components/FilterBar.vue'
import GenomicProfileLabel from './components/GenomicProfileLabel.vue'
import SampleDetails from './components/SampleDetails.vue'
import SampleNumberStatistics from './components/SampleNumberStatistics.vue'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.use(PrimeVue)
app.use(ToastService)

app.component('FilterGroup', FilterGroup)
app.component('FilterBar', FilterBar)
app.component('GenomicProfileLabel', GenomicProfileLabel)
app.component('SampleDetails', SampleDetails)
app.component('SampleNumberStatistics', SampleNumberStatistics)
app.component('IconField', IconField)
app.component('PrimeMenubar', Menubar)
app.component('InputIcon', InputIcon)
app.component('PrimeDialog', Dialog)
app.component('MultiSelect', MultiSelect)
app.component('PrimeButton', Button)
app.component('RadioButton', RadioButton)
app.component('InputText', InputText)
app.component('PrimeDropdown', Dropdown)
app.component('InputNumber', InputNumber)
app.component('DataTable', DataTable)
app.component('PrimePaginator', Paginator)
app.component('PrimeColumn', Column)
app.component('PrimeCard', Card)
app.component('ProgressSpinner', ProgressSpinner)
app.component('ProgressBar', ProgressBar)
app.component('InputSwitch', InputSwitch)
app.component('SplitButton', SplitButton)
app.component('PrimeCalendar', Calendar)
app.component('PrimeChart', Chart)
app.component('AccordionTab', AccordionTab)
app.component('PrimeAccordion', Accordion)
app.component('VIcon', OhVueIcon)
app.component('OverlayPanel', OverlayPanel)
app.component('PrimeChip', Chip)

app.component('PrimeMessage', Message)
app.component('PrimeToast', Toast)
app.component('PrimePanel', Panel)
app.component('PrimeSkeleton', Skeleton)
app.component('PrimeSplitter', Splitter)
app.component('SplitterPanel', SplitterPanel)
app.component('TabView', TabView)
app.component('TabPanel', TabPanel)
app.component('PrimeMenu', Menu)

app.directive('tooltip', Tooltip)
app.directive('animateonscroll', AnimateOnScroll)

app.mixin(ToastMixin)

app.mount('#app')
