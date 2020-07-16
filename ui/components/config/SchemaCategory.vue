<template>
  <b-form-group>
    <details class="isimple-form-section-fit" open>
      <summary>{{ title }}</summary>
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
  },
};
</script>

<style scoped></style>
