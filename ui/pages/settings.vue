<template>
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button @click="setSettings">Save settings & restart</b-button>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button @click="clearCache">Clear cache</b-button>
      </PageHeaderItem>
    </PageHeader>
    <VueFormJsonSchema
      v-model="settings"
      class="settings-form-container"
      :schema="schema"
      :ui-schema="ui_schema"
      :options="{
        castToSchemaType: true,
        showValidationErrors: true,
        allowInvalidModel: true,
        ajv: {
          options: {
            unknownFormats: ['directory-path', 'file-path'], // these get validated by the backend
          },
        },
      }"
    />
    <!--      <b-card>-->
    <!--        <h5>Log</h5>-->
    <!--        <FormSchema ref="form_log" v-model="settings.log" class="form-schema" />-->
    <!--      </b-card>-->
    <!--      <b-card>-->
    <!--        <h5>Cache</h5>-->
    <!--        <FormSchema-->
    <!--          ref="form_cache"-->
    <!--          v-model="settings.cache"-->
    <!--          class="form-schema"-->
    <!--      /></b-card>-->
    <!--      <b-card-->
    <!--        ><h5>Render</h5>-->
    <!--        <FormSchema-->
    <!--          ref="form_render"-->
    <!--          v-model="settings.render"-->
    <!--          class="form-schema"-->
    <!--      /></b-card>-->
    <!--      <b-card-->
    <!--        ><h5>Format</h5>-->
    <!--        <FormSchema-->
    <!--          ref="form_format"-->
    <!--          v-model="settings.format"-->
    <!--          class="form-schema"-->
    <!--      /></b-card>-->

    <!--      <b-card-->
    <!--        ><h5>Database</h5>-->
    <!--        <FormSchema ref="form_db" v-model="settings.db" class="form-schema"-->
    <!--      /></b-card>-->
  </div>
</template>

<script>
import {
  settings_schema,
  get_settings,
  set_settings,
  clear_cache,
} from "../static/api";

import VueFormJsonSchema from "vue-form-json-schema";

import PageHeader from "../components/header/PageHeader";
import PageHeaderItem from "../components/header/PageHeaderItem";
import PageHeaderSeek from "../components/header/PageHeaderSeek";

import { UiSchema } from "../static/ui-schema";

export default {
  name: "dashboard",
  components: {
    PageHeader,
    PageHeaderItem,
    PageHeaderSeek,
    VueFormJsonSchema,
  },
  beforeMount() {
    get_settings().then((settings) => {
      console.log(`settings.get_settings(): settings=`);
      console.log(settings);
      this.settings = settings;
    });
    settings_schema().then((schema) => {
      console.log(`settings.settings_schema(): schema=`);
      console.log(schema);

      this.schema = schema;
      this.ui_schema = UiSchema(schema, {});
    });
  },
  methods: {
    setSettings() {
      console.log("try to set settings");
      console.log(this.settings);

      set_settings(this.settings).then((settings) => {
        this.settings = settings;
      });

      console.log("got back settings");
      console.log(this.settings);
    },
    clearCache() {
      clear_cache();
    },
  },
  data() {
    return {
      settings: {
        cache: {},
        db: {},
        format: {},
        log: {},
        render: {},
      },
      schema: {},
      ui_schema: [],
    };
  },
};
</script>

<style lang="scss" scoped>
$form-element-width: 600px;

@import "../assets/scss/_bootstrap-variables";
@import "../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.form-schema form * {
  display: block;
  width: $form-element-width !important;
  margin: 2px;
}
.card-body {
  padding: 8px;
}
.card {
  min-width: calc(#{$form-element-width} + 20px) !important;
  max-width: calc(#{$form-element-width} + 20px) !important;
  margin-left: 4px;
  margin-top: 4px;
  margin-right: 0;
  margin-bottom: 0;
}
.settings-form-container {
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  overflow-x: hidden;
  overflow-y: hidden;
  align-content: flex-start;
  justify-content: flex-start;
  max-height: calc(100vh - #{$header-height});
  max-width: calc(100vw - #{$sidebar-width});
}
</style>
