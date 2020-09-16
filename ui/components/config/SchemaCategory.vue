<template>
  <b-form-group>
    <details
      class="isimple-form-section-fit"
      :open="open"
      v-on="{ toggle: emit_toggle ? handleToggle : () => {} }"
    >
      <summary class="category-title" :class="{ unclickable: !clickable }">
        <b>{{ title }}</b>
      </summary>
      <div class="isimple-form-indent">
        <slot></slot>
      </div>
    </details>
  </b-form-group>
</template>

<script>
import { debounce } from "throttle-debounce";

export default {
  name: "SchemaCategory",
  props: {
    title: {
      type: String,
      required: true,
    },
    open: {
      type: Boolean,
      required: false,
      default: true,
    },
    emit_toggle: {
      type: Boolean,
      required: false,
      default: false,
    },
    clickable: {
      type: Boolean,
      required: false,
      default: true,
    },
  },
  mounted() {
    // console.log(`SchemaCategory.mounted() title='${this.title}'`);
  },
  methods: {
    handleToggle: debounce(100, true, function () {
      // console.log(`SchemaCategory.handleToggle() title='${this.title}'`);
      this.$emit("toggle");
    }),
  },
  watch: {
    open() {
      // console.log(`SchemaCategory.watch.open() title='${this.title}'`);
    },
  },
};
</script>

<style scoped lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.category-title {
  color: theme-color("gray-700");
}
.unclickable {
  pointer-events: none;
}
</style>
