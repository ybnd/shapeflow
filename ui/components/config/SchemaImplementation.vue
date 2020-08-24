<template>
  <SchemaForm
    v-if="type !== undefined"
    :title="title"
    :data="model"
    :schema="implementation_schema"
    :skip="skip"
    :context="context"
    :property_as_title="property_as_title"
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
    implementation: {
      type: String,
      required: true,
    },
    schema: {
      type: Object,
      required: true,
    },
    context: {
      type: String,
      required: false,
    },
    skip: {
      type: Array,
      default() {
        return [];
      },
    },
    property_as_title: {
      type: Boolean,
      default() {
        return false;
      },
    },
  },
  computed: {
    implementation_schema() {
      console.log(
        `SchemaImplementation.implementation_schema() title=${this.title} type=${this.type}`
      );

      console.log("this.schema=");
      console.log(this.schema);

      console.log("this.model=");
      console.log(this.model);

      return this.schema.implementations[this.type][this.model.type];
    },
  },
};
</script>

<style scoped></style>
