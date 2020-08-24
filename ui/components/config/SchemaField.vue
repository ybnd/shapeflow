<template>
  <component
    :is="new_row ? 'b-form-row' : 'div'"
    :class="new_row ? 'isimple-form-row' : ''"
  >
    <label class="mr-sm-2 isimple-form-label" v-if="title !== ''">
      {{ title }}
    </label>
    <component
      :is="type_component"
      :class="type_class"
      :type="type_type"
      :style="type_style"
      v-model="field"
      :options="
        // enum options
        type_options.hasOwnProperty('enum_options')
          ? type_options.enum_options
          : undefined
      "
      :step="
        // numeric input step
        type_options.hasOwnProperty('step') ? type_options.step : undefined
      "
    />
  </component>
</template>

<script>
import events from "../../static/events";

const types = {
  ENUM: "enum",
  STRING: "string",
  INTEGER: "integer",
  FLOAT: "float",
  NUMBER: "number",
  BOOLEAN: "boolean",
};

export default {
  name: "SchemaField",
  props: {
    title: {
      type: String,
      default: "",
    },
    type: {
      type: String,
      required: true,
    },
    value: {
      required: true,
    },
    options: {
      type: Object,
      default() {
        return {};
      },
    },
    new_row: {
      type: Boolean,
      default() {
        return true;
      },
    },
  },
  mounted() {
    // console.log(`SchemaField ~ title=${this.title} type=${this.type}`);
  },
  computed: {
    type_component() {
      // console.log(`SchemaField.type_component() type=${this.type}`);
      return this.components[this.type];
    },
    type_class() {
      return this.classes[this.type];
    },
    type_options() {
      return { ...this.default_options[this.type], ...this.options };
    },
    type_style() {
      return { ...this.default_style[this.type], ...this.style };
    },
    type_type() {
      return this.types[this.type];
    },
    field: {
      get() {
        return this.value;
      },
      set(v) {
        console.log("SchemaField.set()");
        console.log("v=");
        console.log(v);
        this.$emit("input", v);
      },
    },
  },
  data() {
    return {
      components: {
        [types.ENUM]: "b-form-select",
        [types.STRING]: "b-form-input",
        [types.INTEGER]: "b-form-input",
        [types.FLOAT]: "b-form-input",
        [types.NUMBER]: "b-form-input",
        [types.BOOLEAN]: "b-form-checkbox",
      },
      classes: {
        [types.ENUM]: "isimple-form-field-auto",
        [types.STRING]: "isimple-form-field-input",
        [types.INTEGER]: "isimple-form-field-auto",
        [types.FLOAT]: "isimple-form-field-auto",
        [types.NUMBER]: "isimple-form-field-auto",
        [types.BOOLEAN]: "isimple-form-field-checkbox",
      },
      types: {
        [types.ENUM]: "",
        [types.STRING]: "text",
        [types.INTEGER]: "number",
        [types.FLOAT]: "number",
        [types.NUMBER]: "number",
        [types.BOOLEAN]: "",
      },
      default_options: {
        [types.ENUM]: {},
        [types.STRING]: {},
        [types.INTEGER]: {},
        [types.FLOAT]: { step: 0.1 },
        [types.NUMBER]: { step: 0.1 },
        [types.BOOLEAN]: {},
      },
      default_style: {
        [types.ENUM]: {},
        [types.STRING]: {},
        [types.INTEGER]: { "max-width": "90px" },
        [types.FLOAT]: { "max-width": "180px" },
        [types.NUMBER]: { "max-width": "90px" },
        [types.BOOLEAN]: {},
      },
      parse: {
        [types.ENUM]: (v) => {
          return v;
        },
        [types.STRING]: (v) => {
          return v;
        },
        [types.INTEGER]: (v) => {
          return parseInt(v);
        },
        [types.FLOAT]: (v) => {
          return parseFloat(v);
        },
        [types.NUMBER]: (v) => {
          return parseFloat(v);
        },
        [types.BOOLEAN]: (v) => {
          return v;
        },
      },
    };
  },
};
</script>

<style scoped></style>
