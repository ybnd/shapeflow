<template>
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button
          class="header-button-icon"
          data-toggle="tooltip"
          title="Clear configuration"
          @click="undefined"
        >
          <i class="icon-ban" />
        </b-button>
        <b-button
          class="header-button-icon"
          @click="undoConfig"
          data-toggle="tooltip"
          title="Undo"
          v-hotkey="keymap"
        >
          <i class="icon-action-undo" />
        </b-button>
        <b-button
          class="header-button-icon"
          @click="redoConfig"
          data-toggle="tooltip"
          title="Redo"
          v-hotkey="keymap"
        >
          <i class="icon-action-redo" />
        </b-button>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button @click="undefined">Export</b-button>
      </PageHeaderItem>
    </PageHeader>
    <div class="scrollable">
      <b-card class="name-config isimple-form-section-full">
        <b-row class="isimple-form-row">
          <b-input-group class="isimple-form-group">
            <b-input-group-text class="isimple-form-field-text"
              >name</b-input-group-text
            >
            <b-form-input
              class="isimple-form-field-text"
              v-model="config.name"
            ></b-form-input>
          </b-input-group>
        </b-row>
        <b-row class="isimple-form-row description-label-row">
          <b-input-group-text class="isimple-form-field-text"
            >description</b-input-group-text
          >
        </b-row>
        <b-row class="isimple-form-row description-row">
          <b-input-group class="isimple-form-group">
            <!--todo: not flushed properly when switching analyzers-->
            <b-form-textarea
              class="isimple-form-field-text description-box"
              v-model="config.description"
            ></b-form-textarea>
          </b-input-group>
        </b-row>
      </b-card>
      <b-card class="basic-config isimple-form-section-full">
        <BasicConfig ref="BasicConfig" :config="config" />
      </b-card>
      <VueFormJsonSchema
        v-model="config"
        class="config-form-container"
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
    </div>
  </div>
</template>

<script>
import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";

import BasicConfig from "../../components/config/BasicConfig";
import { UiSchema } from "../../static/ui-schema";

import VueFormJsonSchema from "vue-form-json-schema";

import _ from "lodash";

import VueHotkey from "v-hotkey";
import Vue from "vue";

Vue.use(VueHotkey);

export default {
  name: "dashboard",
  components: { PageHeader, PageHeaderItem, BasicConfig, VueFormJsonSchema },
  beforeMount() {
    this.initConfig();
  },
  methods: {
    undoConfig() {},
    redoConfig() {},
    initConfig() {
      if (this.$store.getters["analyzers/getIndex"](this.id) === -1) {
        this.$router.push(`/`);
      } else {
      }
    },
    handleGetConfig() {
      // request config from backend
      this.$store.dispatch("analyzers/get_config", {
        id: this.id,
      });
    },
    handleSetConfig() {
      // send config to backend
      this.$store.dispatch("analyzers/set_config", {
        id: this.id,
        config: this.config,
      });
    },
  },
  computed: {
    id() {
      return this.$route.query.id;
    },
    keymap() {
      return {
        "ctrl+z": this.undoConfig,
        "ctrl+shift+z": this.redoConfig,
      };
    },
    config() {
      return _.cloneDeep(
        this.$store.getters["analyzers/getAnalyzerConfig"](this.$route.query.id)
      );
    },
    schema() {
      return this.$store.getters["schemas/getConfigSchema"];
    },
    ui_schema() {
      let ui_schema = UiSchema(
        this.schema,
        [
          // these should be handled ~ BasicConfig
          "frame_interval_setting",
          "Nf",
          "dt",
          "video_path",
          "design_path",
          "features",
          "parameters",
          "name",
          "description",
        ],
        {}
      );
      console.log("ui_schema=");
      console.log(ui_schema);
      return ui_schema;
    },
  },
  data: function () {
    return {};
  },
};
</script>

<style lang="scss" scoped>
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.basic-config {
}

.advanced-config {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
}

.config-form-container {
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  overflow-x: hidden;
  overflow-y: show;
  align-content: flex-start;
  justify-content: flex-start;
  max-width: calc(100vw - #{$sidebar-width});
}

.scrollable {
  overflow-x: hidden;
  overflow-y: auto;
  max-width: calc(100vw - #{$sidebar-width});
  max-height: calc(100vh - #{$header-height});
  height: calc(100vh - #{$header-height});
  -ms-overflow-style: none; /* IE 11 */
  scrollbar-width: none; /* Firefox 64 */
}

$description-height: 128px;

.description-row {
  height: calc(#{$description-height});
}
.description-box {
  height: $description-height;
}

.description-label-row {
  margin-bottom: -5px;
}
</style>
