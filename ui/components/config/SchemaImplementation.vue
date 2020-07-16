<template>
  <SchemaForm
    :title="title"
    :data="model"
    :schema="implementation_schema"
    :skip="skip"
  ></SchemaForm>
</template>

<script>
import SchemaForm from "./SchemaForm";

export default {
  name: "SchemaImplementation",
  components: { SchemaForm },
  props: {
    title: {
      type: String,
      required: true,
    },
    model: {
      type: Object,
      required: true,
    },
    type: {
      type: String,
      required: true,
    },
    schema: {
      type: Object,
      required: true,
    },
    skip: {
      type: Array,
      default() {
        return [];
      },
    },
  },
  computed: {
    implementation_schema() {
      return this.schema.implementations[this.type][this.model.type];
    },
  },
};
</script>

<style scoped></style>
