<template>
  <body>
    <main>
      <header>
        <div class="flex flex-wrap justify-content-between">
          <div class="flex align-items-center justify-content-center">
            <div style="font-size: 2rem; color: var(--text-color)">Sonar</div>
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
        <Filters v-if="showFilters" />
        <RouterView />
      </div>
    </main>
    <PrimeToast ref="toast" />
  </body>
</template>

<script lang="ts">
import { RouterView } from 'vue-router'
import 'primeicons/primeicons.css'
import Filters from './components/FilterBar.vue'
import { useSamplesStore } from '@/stores/samples'

export default {
  name: 'App',
  components: {
    RouterView,
    Filters,
  },
  data() {
    return {
      samplesStore: useSamplesStore(),
      menuItems: [
        {
          label: 'Home',
          icon: 'pi pi-home',
          route: '/',
        },
        {
          label: 'Plots',
          icon: 'pi pi-chart-bar',
          route: '/plots',
        },
        {
          label: 'About',
          icon: 'pi pi-star',
          route: '/about',
        },
      ],
    }
  },
  computed: {
    showFilters() {
      return this.$route.name === 'Home' || this.$route.name === 'Plots'
    },
  },
  watch: {
    'samplesStore.errorMessage'(newValue) {
      if (newValue) {
        this.showToastError(newValue)
        // Reset the state to prevent multiple calls
        // this.samplesStore.errorMessage = "";
      }
    },
  },
  mounted() {
    this.samplesStore.updateSamples()
    this.samplesStore
      .updateStatistics()
      .then(() => this.samplesStore.updatePropertyOptions())
      .then(() => this.samplesStore.updateSelectedColumns())
    this.samplesStore.updateFilteredStatistics()
    this.samplesStore.updateLineageOptions()
    this.samplesStore.updateSymbolOptions()
    this.samplesStore.updateRepliconAccessionOptions()
    this.$root.$toastRef = this.$refs.toast ?? null
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
