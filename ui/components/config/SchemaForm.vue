<template>
  <div v-if="properties.length > 0">
    <component
      :is="context !== undefined ? 'SchemaCategory' : 'div'"
      v-if="is_loaded"
      :title="title"
    >
      <template v-if="properties" v-for="property in properties">
        <template v-if="p_type(property) === 'array'">
          <SchemaCategory :title="p_title(property)" :key="property">
            <SchemaForm
              v-for="(item, index) in p_model(property)"
              :title="array_title(property, index)"
              :data="data"
              :schema="schema"
              :skip="skip"
              :context="array_context(property, index)"
              :property_as_title="property_as_title"
              :key="index"
            />
          </SchemaCategory>
        </template>
        <template v-else-if="p_reference(property) !== undefined">
          <SchemaDefinition
            v-if="p_is_hardcoded(property)"
            :title="p_title(property)"
            :model="p_model(property)"
            :definition="p_reference(property)"
            :context="resolve_context(property)"
            :key="property"
          />
          <SchemaImplementation
            v-else-if="p_is_implementation(property)"
            :title="p_title(property)"
            :model="p_model(property)"
            :type="p_type(property)"
            :schema="schema"
            :skip="skip"
            :context="resolve_context(property)"
            :property_as_title="property_as_title"
            :key="property"
          />
          <SchemaForm
            v-else
            :title="p_title(property)"
            :data="data"
            :schema="schema"
            :skip="skip"
            :context="resolve_context(property)"
            :property_as_title="property_as_title"
            :key="property"
          />
        </template>
        <SchemaField
          v-else
          :title="p_title(property)"
          :value="p_model(property)"
          @input="p_set(resolve_context(property), $event)"
          :type="p_type(property)"
          :key="property"
          :options="p_options(property)"
        />
      </template>
      <template v-else>
        <SchemaField
          :title="p_title()"
          :value="p_model()"
          @input="p_set(resolve_context(), $event)"
          :type="p_type()"
          :key="property"
          :options="p_options()"
      /></template>
    </component>
    <div v-else>
      <i class="fa fa-spin fa-spinner" :style="{ 'padding-left': '4px' }" />
    </div>
  </div>
</template>

<script>
import SchemaDefinition from "./SchemaDefinition";
import SchemaImplementation from "./SchemaImplementation";
import SchemaField from "./SchemaField";
import SchemaCategory from "./SchemaCategory";

import get from "lodash/get";
import set from "lodash/set";
import pointer from "json-pointer";

export default {
  name: "SchemaForm",
  components: {
    SchemaImplementation,
    SchemaDefinition,
    SchemaField,
    SchemaCategory,
  },
  props: {
    data: {
      type: Object,
      required: true,
    },
    schema: {
      type: Object,
      required: true,
    },
    skip: {
      type: Array,
      default() {
        return []; // include all fields
      },
    },
    context: {
      type: String,
      default: undefined,
    },
    title: {
      type: String,
      default() {
        return "";
      },
    },
    property_as_title: {
      type: Boolean,
      default() {
        return false;
      },
    },
  },
  mounted() {
    console.log(`SchemaForm ~ ${this.context}`);
  },
  computed: {
    is_loaded() {
      return this.schema.hasOwnProperty("properties");
    },
    properties() {
      console.log(`SchemaForm.properties() @context=${this.context}`);
      console.log(this.schema);

      var props; // intermediate
      var properties;

      if (this.context === undefined) {
        props = this.schema.properties;
      } else {
        let def = this.p_definition(); // todo: placeholder, only works for single-level reference->definition context!

        console.log("def=");
        console.log(def);

        if (def !== undefined) {
          props = def.properties;
        }
      }

      if (props !== undefined) {
        properties = Object.keys(props).filter((p) => !this.skip.includes(p));
      } else {
        properties = [];
      }

      console.log("properties=");
      console.log(properties);

      return properties;
    },
  },
  methods: {
    resolve_context(p) {
      // console.log(`SchemaForm.resolve_context() @context=${this.context}`);
      if (this.context !== undefined) {
        if (p !== undefined) {
          p = [this.context, p].join(".");
        } else {
          return this.context;
        }
      }

      // console.log(`p -> ${p}`);

      return p;
    },
    is_reference(p_schema) {
      return (
        p_schema.hasOwnProperty("$ref") ||
        (p_schema.hasOwnProperty("allOf") &&
          p_schema.allOf.hasOwnProperty("$ref")) ||
        (p_schema.hasOwnProperty("items") &&
          p_schema.items.hasOwnProperty("$ref"))
      );
    },
    get_reference(p_schema) {
      if (p_schema.hasOwnProperty("$ref")) {
        return p_schema.$ref;
      } else if (p_schema.hasOwnProperty("allOf")) {
        return p_schema.allOf[0].$ref;
      } else if (p_schema.hasOwnProperty("items")) {
        return p_schema.items.$ref;
      } else {
        return undefined;
      }
    },
    get_from_schema(p, dereference = true) {
      // console.log(`SchemaForm.get_from_schema() p=${this.resolve_context(p)}`);

      var p_schema;
      p_schema = this.schema;

      // split into levels
      const levels = this.resolve_context(p).split("."); // todo: this doesn't work with array indeces!

      // console.log("levels=");
      // console.log(levels);

      for (let i = 0; i < levels.length; i++) {
        if (this.get_reference(p_schema) !== undefined) {
          p_schema = pointer.get(
            this.schema,
            this.get_reference(p_schema).slice(1)
          );
        }

        // split property & index (optional)
        let prop_index = /(.*)\[([0-9]+)]/g.exec(levels[i]);
        // console.log("prop_index=");
        // console.log(prop_index);

        if (prop_index) {
          let prop = prop_index[1];
          let index = prop_index[2];

          // console.log("p_schema=");
          // console.log(p_schema);

          // console.log(`${levels[i]} is indexed: ${prop} -> ${index}`);

          p_schema = p_schema.properties[prop].items;

          // console.log("p_schema=");
          // console.log(p_schema);
        } else {
          // console.log(`${levels[i]} is not indexed`);
          p_schema = p_schema.properties[levels[i]];
        }
      }

      // console.log("p_schema=");
      // console.log(p_schema);

      if (this.is_reference(p_schema) && dereference) {
        return pointer.get(this.schema, this.get_reference(p_schema).slice(1)); // todo: this is a quick patch to fix ROI not being dereferenced property
      } else {
        return p_schema;
      }
    },
    get_from_data(p) {
      return get(this.data, this.resolve_context(p));
    },
    p_set(p, a) {
      console.log(`SchemaForm.p_set()`);
      console.log("p=");
      console.log(p);
      console.log(`a=`);
      console.log(a);

      set(this.data, p, a);
    },
  },
  data() {
    return {
      p_has_properties: (p) => {
        var p_schema = this.get_from_schema(p);
        return "properties" in p_schema;
      },
      p_reference: (p) => {
        console.log(`SchemaForm.p_reference(), p=${this.resolve_context(p)}`);

        const p_schema = this.get_from_schema(p, false);

        console.log("p_schema=");
        console.log(p_schema); // todo: gets confused when handling definitions

        if (p_schema !== undefined) {
          var r;

          r = this.get_reference(p_schema);

          console.log(`r=${r}`);

          return r;
        } else {
          return undefined;
        }
      },
      p_type: (p) => {
        console.log(`SchemaForm.p_type() p=${this.resolve_context(p)}`);
        const p_schema = this.get_from_schema(p, false);

        console.log("p_schema=");
        console.log(p_schema);

        const type = p_schema.enum ? "enum" : p_schema.type;

        console.log(`type=${type}`);

        return type;
      },
      p_title: (p) => {
        console.log(`SchemaForm.p_title() p=${this.resolve_context(p)}`);

        if (this.property_as_title) {
          return p;
        } else {
          const p_schema = this.get_from_schema(p);

          console.log("p_schema=");
          console.log(p_schema);

          return p_schema.description || p_schema.title.toLowerCase();
        }
      },
      p_options: (p) => {
        const p_schema = this.get_from_schema(p);

        return {
          enum_options: p_schema.enum,
          // todo: is there some kind of float/int 'step' in the schema?
        };
      },
      array_title: (p, i) => {
        // console.log(`SchemaForm.array_title() p=${this.resolve_context(p)}`);
        return `${this.p_title(p)}[${i}]`;
      },
      array_context: (p, i) => {
        console.log(
          `SchemaForm.array_context() p=${p} i=${i} @context=${this.context}`
        );
        return `${this.resolve_context(p)}[${i}]`;
      },
      p_model: (p) => {
        console.log(`SchemaForm.p_model() p=${this.resolve_context(p)}`);
        return this.get_from_data(p);
      },
      p_definition: (p) => {
        console.log(`SchemaForm.p_definition() p=${this.resolve_context(p)}`);

        const r = this.p_reference(p);

        console.log("this.p_reference(p)=");
        console.log(r);

        if (r !== undefined) {
          return pointer.get(this.schema, this.p_reference(p).slice(1));
        } else {
          return undefined;
        }
      },
      p_is_hardcoded: (p) => {
        console.log(`SchemaForm.p_is_hardcoded() p=${this.resolve_context(p)}`);

        const ref = this.p_reference(p);

        console.log("ref=");
        console.log(ref);

        console.log("SchemaDefinition.def=");
        console.log(SchemaDefinition.def);

        const is_hardcoded = Object.values(SchemaDefinition.def).includes(ref);

        console.log(`is_hardcoded=${is_hardcoded}`);

        return is_hardcoded;
      },
      p_is_implementation: (p) => {
        console.log(
          `SchemaForm.p_is_implementation() p=${this.resolve_context(p)}`
        );
        if (this.schema.hasOwnProperty("implementations")) {
          return (
            this.p_reference(p).split("/").pop() in this.schema.implementations
          );
        } else {
          return false;
        }
      },
    };
  },
};
</script>

<style scoped></style>
