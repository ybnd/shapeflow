<template>
  <div class="nav-item nav-dropdown" :to="url" disabled>
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
export default {
  props: {
    name: {
      type: String,
      default: ""
    },
    url: {
      type: String,
      default: ""
    },
    icon: {
      type: String,
      default: ""
    },
    progress: {
      type: Number,
      default: 0
    }
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
    }
  }
};
</script>
