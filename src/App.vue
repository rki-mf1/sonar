<template>
  <RouterView />
</template>

<script lang="ts">
import { RouterView } from 'vue-router'
import 'primeicons/primeicons.css';
export default {
  name: 'App',
  components: {
    RouterView
  }
} 
</script>

<style>

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
}</style>
