<template>
  <component
    :is="new_row ? 'b-form-row' : 'div'"
    :class="new_row ? 'shapeflow-form-row' : ''"
  >
    <label
      class="mr-sm-2 shapeflow-form-label"
      v-if="title !== ''"
      :style="type_label_style"
    >
      {{ title }}
    </label>
    <component
      @wheel="$event.target.blur()"
      :is="type_component"
      class="field"
      :class="type_class"
      :type="type_type"
      :style="type_style"
      v-model="field"
      :options="
        type_options.hasOwnProperty('enum') ? type_options.enum : undefined
      "
      :step="
        // numeric input step
        type_options.hasOwnProperty('step') ? type_options.step : undefined
      "
      @keyup.enter="onKeyUp"
      @focusout="onFocusOut"
      @change="onChange"
    />
  </component>
</template>

<script>
import { COMMIT, ENTER_FOCUSOUT_INTERVAL } from "../../src/events";

const types = {
  ENUM: "enum",
  STRING: "string",
  PATH: "path",
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
    style_: {
      default() {
        return undefined;
      },
    },
    class_: {
      type: String,
      required: false,
      default: "",
    },
    new_row: {
      type: Boolean,
      default() {
        return true;
      },
    },
  },
  mounted() {
    if (this.value === undefined) {
      throw 'SchemaField got no value';
    }

    // console.log(`SchemaField ~ title=${this.title} type=${this.type}`);
    this.valueOut = this.parse[this.type_](this.value);
  },
  methods: {
    onKeyUp(e) {
      if (this.type_commit) {
        this.lastEnter = Date.now();
        if (this.valueOut !== this.value) {
          // console.log("SchemaField.onKeyUp() 'Enter' -> commit");
          this.$emit(COMMIT, this.valueOut);
        }
      }
    },
    onFocusOut() {
      if (
        this.type_commit &&
        Math.abs(Date.now() - this.lastEnter) > ENTER_FOCUSOUT_INTERVAL
      ) {
        if (this.valueOut !== this.value) {
          // console.log("SchemaField.onFocusOut() -> commit");
          this.$emit(COMMIT, this.valueOut);
        }
      }
    },
    onChange(v) {
      if (!this.type_commit) {
        // console.log(`SchemaField.onChange() v=${v} -> commit`);
        if (v !== this.value) {
          // console.log("SchemaField.onFocusOut() -> commit");
          this.$emit(COMMIT, v);
        }
      }
    },
  },
  computed: {
    type_() {
      // console.log(`SchemaField.type_() title=${this.title}`);
      // console.log(this.options);

      if (
        this.options.hasOwnProperty("enum") &&
        this.options.enum !== undefined &&
        this.options.enum.length > 0
      ) {
        return types.ENUM;
      } else if (
        this.options.hasOwnProperty("format") &&
        ["directory-path", "file-path"].includes(this.options.format)
      ) {
        return types.PATH;
      } else {
        return this.type;
      }
    },
    type_commit() {
      return this.commit[this.type_];
    },
    type_component() {
      // console.log(`SchemaField.type_component() type=${this.type}`);
      return this.components[this.type_];
    },
    type_class() {
      return [...this.classes[this.type_], this.class_].join(" ");
    },
    type_options() {
      return { ...this.default_options[this.type_], ...this.options };
    },
    type_style() {
      if (this.style_ !== undefined) {
        // console.log(`SchemaField.type_style() type=${this.type}`);
        // console.log("default=");
        // console.log(this.default_style[this.type]);
        // console.log("style=");
        // console.log(this.style_);
        // console.log("=>");
        // console.log({ ...this.default_style[this.type], ...this.style_ });
      }

      return { ...this.default_style[this.type_], ...this.style_ };
    },
    type_label_style() {
      return this.label_style[this.type_];
    },
    type_type() {
      return this.types[this.type_];
    },
    field: {
      get() {
        // console.log(`SchemaForm.get() type=${this.type}`);
        return this.parse[this.type_](this.value);
      },
      set(v) {
        // console.log(`SchemaForm.set() type=${this.type}`);
        // console.log("v=");
        // console.log(v);

        this.valueOut = this.parse[this.type_](v);
      },
    },
  },
  data() {
    return {
      valueOut: null,
      valueBefore: null,
      lastEnter: 0,
      types_: types,
      commit: {
        [types.ENUM]: false,
        [types.STRING]: true,
        [types.PATH]: true,
        [types.INTEGER]: true,
        [types.FLOAT]: true,
        [types.NUMBER]: true,
        [types.BOOLEAN]: false,
      },
      components: {
        [types.ENUM]: "b-form-select",
        [types.STRING]: "b-form-input",
        [types.PATH]: "b-form-input",
        [types.INTEGER]: "b-form-input",
        [types.FLOAT]: "b-form-input",
        [types.NUMBER]: "b-form-input",
        [types.BOOLEAN]: "b-form-checkbox",
      },
      classes: {
        [types.ENUM]: ["shapeflow-form-field-auto"],
        [types.STRING]: ["shapeflow-form-field-auto"],
        [types.PATH]: ["shapeflow-form-field-wide"],
        [types.INTEGER]: ["shapeflow-form-field-auto", "shapeflow-noarrow"],
        [types.FLOAT]: ["shapeflow-form-field-auto", "shapeflow-noarrow"],
        [types.NUMBER]: ["shapeflow-form-field-auto", "shapeflow-noarrow"],
        [types.BOOLEAN]: ["shapeflow-form-field-checkbox"],
      },
      types: {
        [types.ENUM]: "",
        [types.STRING]: "text",
        [types.PATH]: "text",
        [types.INTEGER]: "number",
        [types.FLOAT]: "number",
        [types.NUMBER]: "number",
        [types.BOOLEAN]: "",
      },
      default_options: {
        [types.ENUM]: {},
        [types.STRING]: {},
        [types.PATH]: {},
        [types.INTEGER]: {},
        [types.FLOAT]: { step: 0.001 },
        [types.NUMBER]: { step: 0.001 },
        [types.BOOLEAN]: {},
      },
      default_style: {
        [types.ENUM]: {},
        [types.STRING]: {},
        [types.PATH]: {},
        [types.INTEGER]: { "max-width": "90px" },
        [types.FLOAT]: { "max-width": "150px" },
        [types.NUMBER]: { "max-width": "90px" },
        [types.BOOLEAN]: {},
      },
      label_style: {
        [types.ENUM]: {},
        [types.STRING]: {},
        [types.PATH]: { "padding-bottom": "0", "margin-bottom": "-10px" },
        [types.INTEGER]: {},
        [types.FLOAT]: {},
        [types.NUMBER]: {},
        [types.BOOLEAN]: {},
      },
      parse: {
        [types.ENUM]: (v) => {
          return v;
        },
        [types.STRING]: (v) => {
          return v;
        },
        [types.PATH]: (v) => {
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
