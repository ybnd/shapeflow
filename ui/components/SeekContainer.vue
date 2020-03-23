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
      default: 0.5
    }
  },
  components: { vuescroll },
  mounted() {
    // seek to middle of file
    seek(this.id, this.position);
  },
  methods: {
    handleScroll(e, position) {
      console.log(`Seeking to ${position}`);
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
