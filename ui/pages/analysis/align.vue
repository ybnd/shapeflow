<template>
  <div class="fixed-page">
    <div class="align-image"></div>
    <div class="controls">
      <div class="seek">
        {{ id }}
        <vue-slider
          v-model="value"
          max="1"
          interval="0.01"
          @change="handleSeek"
        />
      </div>
      <div class="clear">
        <b-button @click="handleClear">Clear</b-button>
      </div>
    </div>
  </div>
</template>

<script>
import VueSlider from "vue-slider-component";

export default {
  name: "dashboard",
  beforeMount() {
    window.onload = () => {
      this.$store.dispatch("analyzers/sync");
    };
  },
  components: {
    VueSlider
  },
  data: function() {
    return {};
  },
  methods: {
    handleSeek({ value }) {},
    handleClear() {}
  },
  computed: {
    id() {
      return this.$route.query.id; // todo: this should get ?id=<...> from the url query
    }
  }
};
</script>

<style></style>
