<template>
  <body>
    <main>
      <header v-if="$route.name !== 'Home'">
        <div class="flex flex-wrap justify-content-between">
          <div class="flex align-items-center justify-content-center">
            <div style="font-size: 2rem; color: var(--text-color)">{{ appTitle }}</div>
          </div>
          <div class="flex align-items-center justify-content-center">
            <PrimeMenubar :model="menuItems">
              <template #item="{ item, props, hasSubmenu }">
                <router-link v-if="item.route" v-slot="{ href, navigate }" :to="item.route" custom>
                  <a
                    class="flex align-items-center gap-1"
                    :href="href"
                    v-bind="props.action"
                    @click="navigate"
                  >
                    <span :class="item.icon" />
                    <span class="ml-1">{{ item.label }}</span>
                  </a>
                </router-link>
                <a v-else :href="item.url" :target="item.target" v-bind="props.action">
                  <span :class="item.icon" />
                  <span>{{ item.label }}</span>
                  <span v-if="hasSubmenu" class="pi pi-fw pi-angle-down" />
                </a>
              </template>
            </PrimeMenubar>
          </div>
        </div>
      </header>

      <div class="content">
        <Filters v-if="showFilters && !showInvalidURLMessage" />
        <div v-if="showInvalidURLMessage">
          <PrimeMessage severity="error">Invalid URL</PrimeMessage>
        </div>
        <RouterView v-else />
      </div>
    </main>
    <PrimeToast ref="toast" />
  </body>
</template>

<script lang="ts">
import router from '@/router'
import { RouterView, type RouteLocationNormalized } from 'vue-router'
import 'primeicons/primeicons.css'
import Filters from './components/FilterBar.vue'
import { useSamplesStore } from '@/stores/samples'
import {
  buildSelectionQuery,
  decodeDatasetsParam,
  safeDecodeURIComponent,
} from '@/util/routeParams'

export default {
  name: 'App',
  components: {
    RouterView,
    Filters,
  },
  data() {
    return {
      samplesStore: useSamplesStore(),
    }
  },
  computed: {
    menuItems() {
      const { accession, data_sets } = this.samplesStore
      const selectionQuery = buildSelectionQuery(accession, data_sets)

      const items = [{ label: 'Home', icon: 'pi pi-home', route: '/' }]
      // dont show menu items 'Table'/'Plots' for 'Sample' view
      if (this.$route.name !== 'Sample') {
        const tableRoute = router.resolve({
          name: 'Table',
          query: selectionQuery,
        }).href
        const plotsRoute = router.resolve({
          name: 'Plots',
          query: selectionQuery,
        }).href
        items.push(
          { label: 'Table', icon: 'pi pi-table', route: tableRoute },
          { label: 'Plots', icon: 'pi pi-chart-bar', route: plotsRoute },
        )
      }
      items.push({ label: 'About', icon: 'pi pi-star', route: '/about' })

      return items
    },
    showFilters() {
      return this.$route.name === 'Table' || this.$route.name === 'Plots'
    },
    appTitle() {
      const organism = this.samplesStore.organism
      return organism ? `Sonar - ${organism}` : 'Sonar'
    },
    showInvalidURLMessage() {
      const routeName = this.$route.name as string | undefined
      if (!['Table', 'Plots'].includes(routeName ?? '')) {
        return false
      }
      if (this.samplesStore.loading) {
        return false
      }
      if (!this.samplesStore.accession) {
        return false
      }
      const total = this.samplesStore.statistics?.samples_total
      return typeof total === 'number' && total === 0
    },
  },
  watch: {
    // whenver navigating to Table or Plots, sync the selection from route with store
    $route: {
      immediate: true,
      handler(route: RouteLocationNormalized) {
        this.syncSelectionFromRoute(route)
      },
    },
    'samplesStore.errorMessage'(newValue) {
      if (newValue) {
        this.showToastError(newValue)
        // Reset the state to prevent multiple calls
        // this.samplesStore.errorMessage = "";
      }
    },
  },
  mounted() {},
  methods: {
    syncSelectionFromRoute(route: RouteLocationNormalized) {
      if ((route.name as string) === 'Home') {
        this.samplesStore.$reset()
        return
      }
      if (!['Table', 'Plots'].includes((route.name as string) ?? '')) {
        return
      }
      const accession =
        typeof route.query?.accession === 'string'
          ? safeDecodeURIComponent(route.query.accession)
          : null
      const datasets = decodeDatasetsParam(route.query?.dataset)
      this.samplesStore.setDataset(this.samplesStore.organism, accession, datasets)
    },
  },
}
</script>

<style>
body {
  width: 100vw;
  margin: -0.5em;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background-color: #adbed3;
}

main {
  flex: 1;
  width: 98vw;
  border-radius: 20px;
  overflow: auto;
  box-shadow: var(--shadow);
}

header {
  padding: 1%;
  background-color: var(--primary-color);
}

.content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  background-color: white;
  min-height: 100vh;
}

:deep(.p-menuitem-content) {
  font-size: 20px;
}

:deep(.p-menubar) {
  padding: 0px;
}

/* .p-menubar {
    background-color: transparent;
  }
  :deep(.p-menubar .p-menubar-root-list > .p-menuitem > .p-menuitem-content .p-menuitem-link .p-menuitem-text) {
    color: white;
  } */

/* ## Scrollbar ## */
/* FIREFOX */
* {
  scrollbar-color: darkgrey white;
  scrollbar-width: thin;
}

/* # CHROME # */
/* width */
::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background-color: rgba(155, 155, 155, 0.5);
  border-radius: 20px;
  border: transparent;
}

/* Track */
::-webkit-scrollbar-track {
  box-shadow: inset 0 0 5px grey;
  border-radius: 10px;
}

/* Handle */
::-webkit-scrollbar-thumb {
  background: grey;
  border-radius: 10px;
}

:deep(.p-button) {
  background: var(--primary-color);
  border: 1px solid var(--primary-color-darker);
}

:deep(.p-button):hover {
  background: var(--primary-color-lighter);
}

:deep(.p-button.p-button-outlined) {
  background: transparent;
  color: var(--primary-color);
}

:deep(.p-button.p-button-outlined):hover {
  background: rgb(248, 247, 247);
}

:deep(.p-button.p-button-warning) {
  background: var(--secondary-color);
  border: 1px solid var(--secondary-color-darker);
}

:deep(.p-button.p-button-warning):hover {
  background: var(--secondary-color-lighter);
}

:deep(.p-inputswitch.p-component.p-highlight .p-inputswitch-slider) {
  background: var(--primary-color);
}

:deep(.p-radiobutton .p-radiobutton-box .p-radiobutton-icon) {
  background: var(--primary-color);
}
</style>
