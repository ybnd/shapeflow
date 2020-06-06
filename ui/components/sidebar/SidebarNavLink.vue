<template>
  <div :to="url" :class="classList" @click="handleClick">
    <i :class="icon"></i> {{ name }}
  </div>
</template>

<script>
import axios from "axios";
import { events } from "../../static/events";

export default {
  name: "sidebar-nav-link",
  props: {
    name: {
      type: String,
      default: "",
    },
    url: {
      type: String,
      default: "",
    },
    icon: {
      type: String,
      default: "",
    },
    classes: {
      type: String,
      default: "",
    },
  },
  created() {
    this.$root.$on(events.sidebar.highlight(this.url), () => {
      this.highlight = true;
    });
    this.$root.$on(events.sidebar.unhighlight(this.url), () => {
      this.highlight = false;
    });
  },
  destroyed() {
    this.$root.$off(events.sidebar.highlight(this.url));
    this.$root.$off(events.sidebar.unhighlight(this.url));
  },
  computed: {
    classList() {
      return [
        "nav-link",
        this.highlight ? "highlight" : "",
        ...this.itemClasses,
      ];
    },
    itemClasses() {
      return this.classes ? this.classes.split(" ") : [];
    },
    isApiLink() {
      return this.url.substring(0, 4) === "/api";
    },
  },
  methods: {
    handleClick() {
      if (this.isApiLink) {
        axios.post(this.url);
      } else {
        this.$router.push(this.url);
      }
    },
  },
  data() {
    return { highlight: false };
  },
};
</script>

<style lang="scss" scoped>
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.highlight {
  background: $gray-700 !important;
  /*color: $gray-800 !important;*/
  /*font-weight: bold;*/
  pointer-events: none;
  i {
    color: theme-color("primary") !important;
  }
}
</style>
