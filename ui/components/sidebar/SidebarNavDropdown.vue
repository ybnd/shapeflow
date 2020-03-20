<template>
  <router-link tag="li" class="nav-item nav-dropdown" :to="url" disabled>
    <div
      class="nav-link nav-dropdown-toggle"
      @load="closedByDefault"
      @click="handleClick"
    >
      <i :class="icon" />{{ name }}
    </div>
    <ul class="nav-dropdown-items">
      <slot></slot>
    </ul>
  </router-link>
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
      e.target.parentElement.toggleClass("nav-dropdown-toggle");
    },
    handleClick(e) {
      e.preventDefault();
      e.target.parentElement.classList.toggle("open");
    }
  }
};
</script>
