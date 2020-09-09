<link rel="stylesheet" href="../assets/scss/_custom.scss" />
<template>
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button @click="setSettings">Save settings & restart</b-button>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button @click="clearDb">Clear database</b-button>
        <b-button @click="clearCache">Clear cache</b-button>
      </PageHeaderItem>
    </PageHeader>
    <SchemaForm
      :data="settings"
      :schema="schema"
      class="settings-form-container"
    />

    <!--    <VueFormJsonSchema-->
    <!--      v-model="settings"-->
    <!--      class="settings-form-container"-->
    <!--      :schema="schema"-->
    <!--      :ui-schema="ui_schema"-->
    <!--      :options="{-->
    <!--        castToSchemaType: true,-->
    <!--        showValidationErrors: true,-->
    <!--        allowInvalidModel: true,-->
    <!--        ajv: {-->
    <!--          options: {-->
    <!--            unknownFormats: ['directory-path', 'file-path'], // these get validated by the backend-->
    <!--          },-->
    <!--        },-->
    <!--      }"-->
    <!--    />-->
  </div>
</template>

<script>
import PageHeader from "../components/header/PageHeader";
import PageHeaderItem from "../components/header/PageHeaderItem";
import PageHeaderSeek from "../components/header/PageHeaderSeek";

import SchemaForm from "../components/config/SchemaForm";

import cloneDeep from "lodash/cloneDeep";

import { clear_cache, clear_db } from "static/api";

export default {
  name: "dashboard",
  components: {
    PageHeader,
    PageHeaderItem,
    PageHeaderSeek,
    SchemaForm,
  },
  mounted() {
    if (this.$store.getters["settings/isUndefined"]) {
      this.$store.dispatch("settings/sync").then(() => {
        // workaround to (re)load frontend on the settings page
        // => settings/sync action called in layouts/default is not resolved yet
        this.settings = this.$store.getters["settings/getSettingsCopy"];
        this.schema = this.$store.getters["settings/getSchemaCopy"];
      });
    } else {
      this.settings = this.$store.getters["settings/getSettingsCopy"];
      this.schema = this.$store.getters["settings/getSchemaCopy"];
    }
  },
  methods: {
    setSettings() {
      this.$store
        .dispatch("settings/set", { settings: this.settings })
        .then(() => {
          this.settings = this.$store.getters["settings/getSettingsCopy"];
        });
    },
    clearCache() {
      clear_cache();
    },
    clearDb() {
      clear_db();
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
  flex-direction: column;
  flex-wrap: wrap;
  overflow-x: scroll;
  overflow-y: hidden;
  -ms-overflow-style: none; /* IE 11 */
  scrollbar-width: none; /* Firefox 64 */
  align-content: flex-start;
  justify-content: flex-start;
  height: calc(100vh - #{$header-height});
  width: calc(100vw - #{$sidebar-width});
}
</style>
