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
        <b-button @click="handleGetConfig">Get configuration</b-button>
        <b-button @click="handleSetConfig">Set configuration</b-button>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button @click="toggleEditJson">{{
          edit_json ? "Hide JSON" : "Edit JSON"
        }}</b-button>
      </PageHeaderItem>
    </PageHeader>
    <div class="scrollable">
      <b-card class="name-config isimple-form-section">
        <b-row class="isimple-form-row">
          <b-input-group class="isimple-form-group">
            <b-input-group-text class="isimple-form-field-text"
              >name</b-input-group-text
            >
            <b-form-input
              class="isimple-form-field-text"
              v-model.lazy="config.name"
              @change="handleSetConfig"
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
              v-model.lazy="config.description"
              @change="handleSetConfig"
            ></b-form-textarea>
          </b-input-group>
        </b-row>
      </b-card>
      <b-card class="basic-config isimple-form-section">
        <BasicConfig
          ref="BasicConfig"
          :config="config"
          :static-paths="true"
          @change="handleSetConfig"
        />
      </b-card>
      <b-collapse
        id="advanced-settings"
        class="advanced-config-collapse"
        :visible="edit_json"
        v-if="edit_json"
      >
        <!--        <b-form-textarea-->
        <!--          class="isimple-form-field-text advanced-config-box"-->
        <!--          spellcheck="false"-->
        <!--          v-model.lazy="config_json"-->
        <!--          @change="handleChangeJson"-->
        <!--          style="font-family: monospace;"-->
        <!--        />-->
        <!--        <b-card class="isimple-form-section-full advanced-config-box">-->
        <!--          stuff-->
        <!--        </b-card>-->
        <b-card class="isimple-form-section advanced-config-box">
          <VueFormJsonSchema
            v-model="config"
            class="config-form-container"
            :schema="schema"
            :ui-schema="ui_schema"
            :options="{
              castToSchemaType: false,
              showValidationErrors: false,
              allowInvalidModel: true,
              ajv: {
                options: {
                  unknownFormats: ['directory-path', 'file-path'], // these get validated by the backend
                },
              },
            }"
          />
        </b-card>
      </b-collapse>
    </div>
  </div>
</template>

<script>
import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";
import BasicConfig from "../../components/config/BasicConfig";

import { undo_config, redo_config } from "../../static/api";

import { UiSchema } from "../../static/ui-schema";

import { events } from "../../static/events";

import cloneDeep from "lodash/cloneDeep";

import VueHotkey from "v-hotkey";
import Vue from "vue";

import AsyncComputed from "vue-async-computed";

import beautify from "json-beautify";

import VueFormJsonSchema from "vue-form-json-schema";

Vue.use(VueHotkey);
Vue.use(AsyncComputed);

export default {
  name: "dashboard",
  components: {
    PageHeader,
    PageHeaderItem,
    BasicConfig,
    VueFormJsonSchema,
  },
  beforeMount() {
    this.handleInit();
  },
  beforeDestroy() {
    this.handleCleanUp();
  },
  methods: {
    undoConfig() {
      undo_config(this.id).then(this.handleGetConfig());
    },
    redoConfig() {
      redo_config(this.id).then(this.handleGetConfig());
    },
    handleInit() {
      this.previous_id = this.id;

      if (this.$store.getters["analyzers/getIndex"](this.id) === -1) {
        this.$router.push(`/`);
      } else {
        this.$root.$emit(events.sidebar.open(this.id));
        this.edit_json = this.$store.getters[
          "settings/getSettings"
        ].app.edit_json;
        this.handleGetConfig();
      }
    },
    handleCleanUp() {},
    handleGetConfig() {
      const t0 = Date.now();
      // request config from backend
      this.$store
        .dispatch("analyzers/get_config", {
          id: this.id,
        })
        .then(() => {
          this.config = cloneDeep(
            this.$store.getters["analyzers/getAnalyzerConfig"](this.id)
          );
          this.config_json = beautify(this.config, null, 2, 120);

          const t1 = Date.now();

          if (this.schema) {
            this.ui_schema = UiSchema(
              this.schema,
              this.config,
              [
                // these should be handled ~ BasicConfig
                "frame_interval_setting",
                "Nf",
                "dt",
                "video_path",
                "design_path",
                "features",
                "parameters",
                // these should be handled separately
                "name",
                "description",
              ],
              { "": ["design", "transform"] }
            );
            console.log("ui_schema=");
            console.log(this.ui_schema);
          }

          console.log(`ui_schema: ${Date.now() - t1} elapsed`);
          console.log(`total: ${Date.now() - t0} elapsed`);
        });
    },
    handleSetConfig() {
      // send config to backend
      this.$store
        .dispatch("analyzers/set_config", {
          id: this.id,
          config: this.config,
        })
        .then(() => {
          this.config = cloneDeep(
            this.$store.getters["analyzers/getAnalyzerConfig"](this.id)
          );
          this.config_json = beautify(this.config, null, 2, 120);
        });
    },
    toggleEditJson() {
      this.edit_json = !this.edit_json;
    },
    handleChangeJson() {
      this.$store
        .dispatch("analyzers/set_config", {
          id: this.id,
          config: JSON.parse(this.config_json),
        })
        .then(() => {
          this.config = cloneDeep(
            this.$store.getters["analyzers/getAnalyzerConfig"](this.id)
          );
          this.config_json = beautify(this.config, null, 2, 120);
        });
    },
  },
  watch: {
    "$route.query.id"() {
      console.log(`id has changed ${this.id}`);

      // this.$forceUpdate();
      this.handleCleanUp();
      this.handleInit();
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
    schema() {
      return this.$store.getters["schemas/getConfigSchema"];
    },
  },
  data() {
    return {
      config: {},
      config_json: undefined,
      edit_json: false,
      ui_schema: [],
    };
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
}

.scrollable {
  // it's not scrollable tho
  display: flex;
  flex-direction: column;
  max-width: calc(100vw - #{$sidebar-width});
  max-height: calc(100vh - #{$header-height});
  height: calc(100vh - #{$header-height});
  /*-ms-overflow-style: none; !* IE 11 *!*/
  /*scrollbar-width: none; !* Firefox 64 *!*/
  flex-grow: 0;
}

$description-height: 64px;

.description-row {
  height: calc(#{$description-height});
}
.description-box {
  height: $description-height;
}
.advanced-config-box {
  margin-top: 0;
}

.advanced-config-box > .card-body {
}

.advanced-config-card {
}

.advanced-config-collapse {
  margin-top: 4px;
  margin-bottom: 4px;
  overflow-y: scroll;
  overflow-x: hidden;
  max-width: calc(100vw - #{$sidebar-width} - 4px);
}

.description-label-row {
  margin-bottom: -5px;
}
</style>
