<template>
  <b-form-group>
    <details
      class="isimple-form-section-fit"
      :open="open"
      @toggle="handleToggle"
    >
      <summary class="category-title">
        <b>{{ title }}</b>
      </summary>
      <div class="isimple-form-indent">
        <slot></slot>
      </div>
    </details>
  </b-form-group>
</template>

<script>
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
  },
  mounted() {
    // console.log(`SchemaCategory.mounted() title=${this.title}`);

    if (this.emit_toggle && this.open) {
      this.first_toggle = true;
    }
  },
  methods: {
    handleToggle(e) {
      // console.log(`SchemaCategory.handleToggle() title=${this.title}`);
      // console.log(e);

      if (this.emit_toggle) {
        if (this.first_toggle) {
          // workaround
          // otherwise, the automatic first toggle causes an infinite loop of toggles
          this.first_toggle = false;
        } else {
          this.$emit("toggle");
        }
      }
    },
  },
  data() {
    return {
      first_toggle: false,
    };
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
</style>
