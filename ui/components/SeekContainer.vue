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
import { seek } from "../static/api";

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
    },
    callback: {
      type: Function,
      default: undefined
    }
  },
  components: { vuescroll },
  mounted() {
    // seek to middle of file
    console.log("Seeking to middle of file");
    seek(this.id, this.position);
  },
  methods: {
    handleScroll(e, position) {
      console.log(`Seeking to ${position}`);
      seek(id, position).then(new_position => {
        this.position = new_position;
      });
      if (this.callback !== undefined) {
        this.callback();
      }
    }
  }
};
</script>

<style scoped>
.seek-container {
  position: relative;
}
</style>
