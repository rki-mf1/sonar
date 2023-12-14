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