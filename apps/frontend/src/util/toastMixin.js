// make it as a global function
export default {
  methods: {
    showToastError(message) {
      if (this.$root.$toastRef) {
        this.$root.$toastRef.add({
          severity: 'error',
          summary: 'Error',
          detail: message,
          life: 10000
        })
      }
    }
  }
}
