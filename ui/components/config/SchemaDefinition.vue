<template>
  <div>
    <template v-if="match(def.COO)">
      <!--      todo: check if model fits definition? -->
      <b-row class="isimple-form-row">
        <b-input-group class="isimple-form-group">
          <label class="mr-sm-2 isimple-form-label" :style="{ width: '60px' }">
            {{ title }} (x,y)
          </label>
          <SchemaField
            :value="model.x"
            @input="p_set('x', $event)"
            type="float"
            :options="{ step: 1e-24 }"
          ></SchemaField>
          <div class="isimple-form-gap" />
          <SchemaField
            :value="model.y"
            @input="p_set('y', $event)"
            type="float"
            :options="{ step: 1e-24 }"
          ></SchemaField>
        </b-input-group>
      </b-row>
    </template>
    <template v-else-if="match(def.HSVCOLOR)">
      <b-row class="isimple-form-row">
        <b-input-group class="isimple-form-group">
          <label class="mr-sm-2 isimple-form-label" :style="{ width: '90px' }">
            {{ title }} (h,s,v)
          </label>
          <SchemaField
            :value="model.h"
            @input="p_set('h', $event)"
            type="integer"
          ></SchemaField>
          <div class="isimple-form-gap" />
          <SchemaField
            :value="model.s"
            @input="p_set('s', $event)"
            type="integer"
          ></SchemaField>
          <div class="isimple-form-gap" />
          <SchemaField
            :value="model.v"
            @input="p_set('v', $event)"
            type="integer"
          ></SchemaField>
        </b-input-group>
      </b-row>
    </template>
    <template v-else-if="match(def.FLIPCONFIG)">
      <b-row class="isimple-form-row">
        <b-input-group class="isimple-form-group">
          <label class="mr-sm-2 isimple-form-label">
            {{ title }} horizontally
          </label>
          <SchemaField
            :value="model.horizontal"
            @input="p_set('horizontal', $event)"
            type="boolean"
          ></SchemaField>
          <label class="mr-sm-2 isimple-form-label">
            vertically
          </label>
          <SchemaField
            :value="model.vertical"
            @input="p_set('vertical', $event)"
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
      type: Object,
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
    console.log(
      `SchemaDefinition ~ ${this.definition}; ${this.context}: ${this.title}`
    );
    console.log("model=");
    console.log(this.model);
  },
  methods: {
    match(match_definition) {
      if (this.definition === match_definition) {
        const fields_ok = fields[this.definition]
          .map((v) => this.model.hasOwnProperty(v))
          .reduce((g, v) => g && v);
        if (!fields_ok) {
          console.warn(
            "SchemaDefinition.match(): model doesn't include required fields"
          );
          console.log(this.model);
          console.log(fields[this.definition]);
        }
        return fields_ok;
      } else {
        return false;
      }
    },
    p_set(p, a) {
      set(this.model, p, a);
    },
  },
  data() {
    return { def: def };
  },
};
</script>

<style scoped></style>
