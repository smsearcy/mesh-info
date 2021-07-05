/*
  Disclaimer: I'm not a frontend developer and I'm learning Vue.js
  (And I want the simplicity of no Javascript build process.)
  -Scott
*/

const app = Vue.createApp({
  data() {
    return {
      menuExpanded: false
    }
  },
  methods: {
    toggleMenu() {
      this.menuExpanded = !this.menuExpanded
    }
  }
})

const vm = app.mount("#app")
