import 'primeflex/primeflex.css'
import './util/custom_theme.css'
import 'primeicons/primeicons.css' //icons
import ToastMixin from './util/toastMixin'

import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'
import Menubar from 'primevue/menubar'
import Button from 'primevue/button'
import RadioButton from 'primevue/radiobutton'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import ProgressSpinner from 'primevue/progressspinner'
import ProgressBar from 'primevue/progressbar'
import DataTable from 'primevue/datatable'
import Paginator from 'primevue/paginator'
import Column from 'primevue/column'
import Card from 'primevue/card'
import ToggleSwitch from 'primevue/toggleswitch'
import SplitButton from 'primevue/splitbutton'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Dialog from 'primevue/dialog'
import MultiSelect from 'primevue/multiselect'
import DatePicker from 'primevue/datepicker'
import Chart from 'primevue/chart'
import Tooltip from 'primevue/tooltip'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import Popover from 'primevue/popover'
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
import Slider from 'primevue/slider'
import Splitter from 'primevue/splitter'
import SplitterPanel from 'primevue/splitterpanel'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
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

app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      darkModeSelector: false,
    },
  },
})
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
app.component('PrimeDropdown', Select)
app.component('InputNumber', InputNumber)
app.component('DataTable', DataTable)
app.component('PrimePaginator', Paginator)
app.component('PrimeColumn', Column)
app.component('PrimeCard', Card)
app.component('ProgressSpinner', ProgressSpinner)
app.component('ProgressBar', ProgressBar)
app.component('InputSwitch', ToggleSwitch)
app.component('SplitButton', SplitButton)
app.component('PrimeCalendar', DatePicker)
app.component('PrimeChart', Chart)
app.component('PrimeAccordion', Accordion)
app.component('AccordionPanel', AccordionPanel)
app.component('AccordionHeader', AccordionHeader)
app.component('AccordionContent', AccordionContent)
app.component('VIcon', OhVueIcon)
app.component('PrimePopover', Popover)
app.component('PrimeChip', Chip)

app.component('PrimeMessage', Message)
app.component('PrimeToast', Toast)
app.component('PrimePanel', Panel)
app.component('PrimeSkeleton', Skeleton)
app.component('PrimeSlider', Slider)
app.component('PrimeSplitter', Splitter)
app.component('SplitterPanel', SplitterPanel)
app.component('PrimeTabs', Tabs)
app.component('TabList', TabList)
app.component('PrimeTab', Tab)
app.component('TabPanels', TabPanels)
app.component('TabPanel', TabPanel)
app.component('PrimeMenu', Menu)

app.directive('tooltip', Tooltip)
app.directive('animateonscroll', AnimateOnScroll)

app.mixin(ToastMixin)

app.mount('#app')
