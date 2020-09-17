<template>
  <div>
    <template v-if="model === undefined">
      <b-row class="shapeflow-form-row">
        <b-input-group class="shapeflow-form-group">
          <label class="mr-sm-2 shapeflow-form-label">
            {{ title }} (undefined)
          </label>
        </b-input-group>
      </b-row>
    </template>
    <template v-else-if="match(def.COO)">
      <!--      todo: check if model fits definition? -->
      <b-row class="shapeflow-form-row">
        <b-input-group class="shapeflow-form-group">
          <label
            class="mr-sm-2 shapeflow-form-label"
            :style="{ width: '60px', 'margin-right': '0 !important' }"
          >
            {{ title }} (x,y)
          </label>
          <SchemaField
            :value="model.x"
            @commit="p_set('x', $event)"
            type="float"
            :options="{ step: 1e-24 }"
          ></SchemaField>
          <div class="shapeflow-form-gap" />
          <SchemaField
            :value="model.y"
            @commit="p_set('y', $event)"
            type="float"
            :options="{ step: 1e-24 }"
          ></SchemaField>
        </b-input-group>
      </b-row>
    </template>
    <template v-else-if="match(def.HSVCOLOR)">
      <b-row class="shapeflow-form-row">
        <b-input-group class="shapeflow-form-group">
          <label
            class="mr-sm-2 shapeflow-form-label"
            :style="{ width: '90px', 'margin-right': '0 !important' }"
          >
            {{ title }} (h,s,v)
          </label>
          <!-- todo: alignment issues  -- fields jump down by 2px -->
          <SchemaField
            :value="model.h"
            @commit="p_set('h', $event)"
            :style_="{
              width: '50px',
              'margin-top': '-2px' /* todo: alignment issue */,
            }"
            type="integer"
          ></SchemaField>
          <div class="shapeflow-form-gap" />
          <SchemaField
            :value="model.s"
            @commit="p_set('s', $event)"
            :style_="{
              width: '50px',
              'margin-top': '-2px' /* todo: alignment issue */,
            }"
            type="integer"
          ></SchemaField>
          <div class="shapeflow-form-gap" />
          <SchemaField
            :value="model.v"
            @commit="p_set('v', $event)"
            :style_="{
              width: '50px',
              'margin-top': '-2px' /* todo: alignment issue */,
            }"
            type="integer"
          ></SchemaField>
        </b-input-group>
      </b-row>
    </template>
    <template v-else-if="match(def.FLIPCONFIG)">
      <b-row class="shapeflow-form-row">
        <b-input-group class="shapeflow-form-group">
          <label
            class="mr-sm-2 shapeflow-form-label"
            :style="{ 'margin-right': '0 !important', 'padding-top': '4px' }"
          >
            {{ title }} horizontally
          </label>
          <SchemaField
            :value="model.horizontal"
            @commit="p_set('horizontal', $event)"
            type="boolean"
          ></SchemaField>
          <label
            class="mr-sm-2 shapeflow-form-label"
            :style="{ 'margin-right': '0 !important', 'padding-top': '4px' }"
          >
            vertically
          </label>
          <SchemaField
            :value="model.vertical"
            @commit="p_set('vertical', $event)"
            type="boolean"
          ></SchemaField>
        </b-input-group>
      </b-row>
    </template>
  </div>
</template>

<script>
import SchemaField from "./SchemaField";
import set from "lodash/set";

import { COMMIT } from "static/events";

const def = {
  COO: "#/definitions/Coo",
  HSVCOLOR: "#/definitions/HsvColor",
  FLIPCONFIG: "#/definitions/FlipConfig",
};

const fields = {
  [def.COO]: ["x", "y"],
  [def.HSVCOLOR]: ["h", "s", "v"],
  [def.FLIPCONFIG]: ["horizontal", "vertical"],
};

export default {
  name: "SchemaDefinition",
  components: { SchemaField },
  def: def,
  props: {
    title: {
      type: String,
      required: true,
    },
    model: {
      required: true,
    },
    definition: {
      type: String,
      required: true,
    },
    context: {
      type: String,
      required: false,
    },
  },
  mounted() {
    // console.log(
    //   `SchemaDefinition ~ ${this.definition}; ${this.context}: ${this.title}`
    // );
    // console.log("model=");
    // console.log(this.model);
  },
  methods: {
    match(match_definition) {
      if (this.definition === match_definition) {
        const fields_ok = fields[this.definition]
          .map((v) => this.model.hasOwnProperty(v))
          .reduce((g, v) => g && v);
        if (!fields_ok) {
          // console.warn(
          //   "SchemaDefinition.match(): model doesn't include required fields"
          // );
          // console.log(this.model);
          // console.log(fields[this.definition]);
        }
        return fields_ok;
      } else {
        return false;
      }
    },
    p_set(p, a) {
      set(this.model, p, a);
      // console.log("SchemaDefinition.p_set()");
      this.$emit(COMMIT);
    },
  },
  data() {
    return { def: def };
  },
};
</script>

<style scoped></style>
