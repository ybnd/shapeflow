<template>
  <div
    class="seek-container"
    v-scroll:debounce="{ fn: handleScroll, debounce: debounce }"
  >
    <slot></slot>
  </div>
</template>

<script>
import vuescroll from "vue-scroll";
import { seek } from "../assets/api";

export default {
  name: "seek",
  props: {
    id: {
      type: String,
      default: ""
    },
    debounce: {
      type: Number,
      default: 100
    },
    position: {
      type: Number,
      default: 0.0
    }
  },
  components: { vuescroll },
  methods: {
    handleScroll(e, position) {
      seek(id, position).then(new_position => {
        this.position = new_position;
      });
    }
  }
};
</script>

<style scoped>
.seek-container {
  position: relative;
}
</style>
