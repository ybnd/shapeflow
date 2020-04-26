<template>
  <div class="fixed-page">
    <header>Configure</header>
    <p>some dashboard things go here, I guess?</p>
  </div>
</template>

<script>
export default {
  name: "dashboard",
  components: {},
  beforeMount() {
    this.initConfig();
  },
  methods: {
    initConfig() {
      if (this.$store.getters["queue/getIndex"](this.id) === -1) {
        this.$router.push(`/`);
      } else {
      }
    }
  },
  computed: {
    id() {
      return this.$route.query.id;
    }
  },
  data: function() {
    return {};
  }
};
</script>

<style></style>
