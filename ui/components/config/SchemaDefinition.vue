<template>
  <div>
    <template v-if="definition === def.COO">
      <b-row class="isimple-form-row">
        <b-input-group class="isimple-form-group">
          <label class="mr-sm-2 isimple-form-label" :style="{ width: '60px' }">
            {{ title }} (x,y)
          </label>
          <SchemaField
            :model="model.x"
            type="float"
            :options="{ step: 1e-24 }"
          ></SchemaField>
          <div class="isimple-form-gap" />
          <SchemaField
            :model="model.y"
            type="float"
            :options="{ step: 1e-24 }"
          ></SchemaField>
        </b-input-group>
      </b-row>
    </template>
    <template v-else-if="definition === def.HSVCOLOR">
      <b-row class="isimple-form-row">
        <b-input-group class="isimple-form-group">
          <label class="mr-sm-2 isimple-form-label" :style="{ width: '90px' }">
            {{ title }} (h,s,v)
          </label>
          <SchemaField :model="model.h" type="integer"></SchemaField>
          <div class="isimple-form-gap" />
          <SchemaField :model="model.s" type="integer"></SchemaField>
          <div class="isimple-form-gap" />
          <SchemaField :model="model.v" type="integer"></SchemaField>
        </b-input-group>
      </b-row>
    </template>
    <template v-else-if="definition === def.FLIPCONFIG">
      <b-row class="isimple-form-row">
        <b-input-group class="isimple-form-group">
          <label class="mr-sm-2 isimple-form-label">
            {{ title }} horizontally
          </label>
          <SchemaField :model="model.horizontal" type="integer"></SchemaField>
          <label class="mr-sm-2 isimple-form-label">
            vertically
          </label>
          <SchemaField :model="model.vertical" type="integer"></SchemaField>
        </b-input-group>
      </b-row>
    </template>
  </div>
</template>

<script>
import SchemaField from "./SchemaField";

const def = {
  COO: "#/definitions/Coo",
  HSVCOLOR: "#/definitions/HsvColor",
  FLIPCONFIG: "#/definitions/FlipConfig",
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
  },
};
</script>

<style scoped></style>
