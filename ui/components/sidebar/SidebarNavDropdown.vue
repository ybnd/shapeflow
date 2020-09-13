<template>
  <div class="nav-item nav-dropdown" :to="url" :ref="ref" disabled>
    <div
      class="nav-link nav-dropdown-toggle"
      @load="closedByDefault"
      @click="handleClick"
    >
      <i v-if="icon" :class="icon" />{{ name }}
    </div>
    <ul class="nav-dropdown-items">
      <slot></slot>
    </ul>
  </div>
</template>

<script>
import { events } from "../../static/events";

export default {
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
    progress: {
      type: Number,
      default: 0,
    },
  },
  created() {
    // console.log("SidebarNavDropdown listening for open events on ");
    // console.log(this.event.open);
    this.$root.$on(this.event.open, this.handleOpen);
  },
  destroyed() {
    this.$root.$off(this.event.open, this.handleOpen);
  },
  methods: {
    closedByDefault(e) {
      e.preventDefault();
      // todo: doesn't work because it gets classed with 'nuxt-link-exact-active' 'active' 'open' by default...
      e.target.parentElement.toggleClass("nav-dropdown-toggle");
    },
    handleClick(e) {
      e.preventDefault();
      e.target.parentElement.classList.toggle("open");
    },
    handleOpen() {
      // console.log("SidebarNavDropdown -- handling open event");
      this.$refs[this.ref].classList.add("open");
    },
  },
  computed: {
    ref() {
      return `dropdown-${this.name}`;
    },
    event() {
      return { open: events.sidebar.open(this.name) };
    },
  },
};
</script>
