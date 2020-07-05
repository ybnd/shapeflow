<template>
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button @click="setSettings">Save settings & restart</b-button>
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
  mounted() {
    if (this.$store.getters["settings/isUndefined"]) {
      this.$store.dispatch("settings/sync").then(() => {
        // workaround to (re)load frontend on the settings page
        // => settings/sync action called in layouts/default is not resolved yet
        this.settings = this.$store.getters["settings/getSettings"];
        this.schema = this.$store.getters["settings/getSchema"];

        this.ui_schema = UiSchema(this.schema, {});

        console.log("ui_schema=");
        console.log(this.ui_schema);
      });
    } else {
      this.settings = this.$store.getters["settings/getSettings"];
      this.schema = this.$store.getters["settings/getSchema"];

      this.ui_schema = UiSchema(this.schema, {});
    }
  },
  methods: {
    setSettings() {
      this.$store
        .dispatch("settings/set", { settings: this.settings })
        .then((settings) => {
          this.settings = settings;
        });
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
