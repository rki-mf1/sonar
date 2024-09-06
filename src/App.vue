<template>

  <body>
    <main>
      <header>
        <div class="flex  flex-wrap justify-content-between">
          <div class="flex align-items-center justify-content-center">
            <div style="font-size: 2rem; color: var(--text-color);">
              <i class="pi pi-spinner" style="font-size: 3rem; color: var(--text-color);"></i>ovSonar
            </div>
          </div>
          <div class="flex align-items-center justify-content-center">
            <Menubar :model="menuItems">
              <template #item="{ item, props, hasSubmenu }">
                <router-link v-if="item.route" v-slot="{ href, navigate }" :to="item.route" custom>
                  <a class="flex align-items-center gap-1" :href="href" v-bind="props.action" @click="navigate">
                    <span :class="item.icon" />
                    <span class="ml-1">{{ item.label }}</span>
                  </a>
                </router-link>
                <a v-else :href="item.url" :target="item.target" v-bind="props.action">
                  <span :class="item.icon" />
                  <span >{{ item.label }}</span>
                  <span v-if="hasSubmenu" class="pi pi-fw pi-angle-down" />
                </a>
              </template>
            </Menubar>
          </div>
        </div>
      </header>

      <div class="content">
        <RouterView />
      </div>
    </main>
  </body>

</template>

<script lang="ts">

import { RouterView } from 'vue-router'
import 'primeicons/primeicons.css';

export default {
  name: 'App',
  components: {
    RouterView
  },
  data() {
    return {
      menuItems: [
        {
          label: 'Home',
          icon: 'pi pi-home',
          route: '/'
        },
        {
          label: 'About',
          icon: 'pi pi-star',
          route: '/about'
        }
      ]
    }
  }
} 
</script>


<style scoped>
body {
  height: 100vh;
  width: 100vw;
  margin: -0.5em;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #adbed3;
}

main {
  height: 97vh;
  width: 98vw;
  display: flex;
  align-items: stretch;
  flex-direction: column;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: var(--shadow);
}

header {
  padding: 1%;
  background-color: var(--primary-color);
}

.content {
  width: 100%;
  height: 90%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-evenly;
  background-color: white;
}

.menu {
  margin-left: 35%;
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
</style>
