<template>
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button
          class="header-button-icon"
          data-toggle="tooltip"
          title="Reset to defaults"
          @click="handleResetToDefaults"
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
        <div class="header-button-icon config-spinner">
          <i :class="{ 'fa fa-spinner fa-spin': waiting }" />
        </div>
      </PageHeaderItem>
    </PageHeader>
    <div class="scrollable">
      <b-card class="name-config shapeflow-form-section">
        <b-row class="shapeflow-form-row">
          <b-input-group class="shapeflow-form-group">
            <b-input-group-text class="shapeflow-form-field-text"
              >name</b-input-group-text
            >
            <b-form-input
              class="shapeflow-form-field-text"
              v-model="config.name"
              @keyup="onKeyUp"
              @focusout="onFocusOut"
            ></b-form-input>
          </b-input-group>
        </b-row>
        <b-row class="shapeflow-form-row description-row">
          <b-input-group class="shapeflow-form-group">
            <!--todo: not flushed properly when switching analyzers-->
            <b-form-textarea
              class="shapeflow-form-field-text description-box"
              v-model="config.description"
              spellcheck="false"
              placeholder="add a description here"
              @focusout="onFocusOut"
            ></b-form-textarea>
          </b-input-group>
        </b-row>
      </b-card>
      <b-card class="basic-config-container shapeflow-form-section">
        <div class="basic-config-gap">
          <BasicConfig
            v-if="this.ready.schema && this.ready.config"
            ref="BasicConfig"
            :config="config"
            :static-paths="true"
            @commit="handleUpdate"
          />
        </div>
      </b-card>
      <b-card
        class="shapeflow-form-section advanced-config-box advanced-config-collapse"
      >
        <!--          <VueFormJsonSchema-->
        <!--            v-model="config"-->
        <!--            class="config-form-container"-->
        <!--            :schema="schema"-->
        <!--            :ui-schema="ui_schema"-->
        <!--            :options="{-->
        <!--              castToSchemaType: false,-->
        <!--              showValidationErrors: false,-->
        <!--              allowInvalidModel: true,-->
        <!--              ajv: {-->
        <!--                options: {-->
        <!--                  unknownFormats: ['directory-path', 'file-path'], // these get validated by the backend-->
        <!--                },-->
        <!--              },-->
        <!--            }"-->
        <!--          />-->

        <SchemaForm
          v-if="this.ready.schema && this.ready.config"
          :data="config"
          :schema="schema"
          :skip="[
            'name', // handled separately; also applies to masks[*].name, which shouldn't be changed
            'description', // handled separately
            'features', // handled by BasicConfig.vue
            'feature_parameters', // handled by BasicConfig.vue
            'frame_interval_setting', // handled by BasicConfig.vue
            'dt', // handled by BasicConfig.vue
            'Nf', // handled by BasicConfig.vue
            'design_path', // handled by BasicConfig.vue
            'video_path', // handled by BasicConfig.vue
            // 'masks',
            // 'parameters',
            // 'transform',
            // 'design',
            // 'video',
            // 'filter', // todo: this one's bugged
          ]"
          class="config-form-container"
          :property_as_title="true"
          @commit="handleUpdate"
        />
      </b-card>
    </div>
  </div>
</template>

<script>
import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";
import BasicConfig from "../../components/config/BasicConfig";
import SchemaForm from "../../components/config/SchemaForm";

import { api } from "../../static/api";

import { events, ENTER_FOCUSOUT_INTERVAL, COMMIT } from "../../static/events";

import cloneDeep from "lodash/cloneDeep";

import { throttle, debounce } from "throttle-debounce";

import Vue from "vue";
import VueHotkey from "v-hotkey";
Vue.use(VueHotkey);

export default {
  name: "dashboard",
  components: {
    PageHeader,
    PageHeaderItem,
    BasicConfig,
    SchemaForm,
  },
  mounted() {
    this.handleInit();
  },
  destroyed() {
    this.handleCleanUp();
  },
  methods: {
    onKeyUp(e) {
      if (e.key === "Enter") {
        // console.log("configure.onKeyUp() 'Enter'");
        this.lastEnter = Date.now();
        this.handleUpdate();
      }
    },
    onFocusOut() {
      // console.log("configure.onFocusOut()");
      if (Math.abs(Date.now() - this.lastEnter) > ENTER_FOCUSOUT_INTERVAL) {
        this.handleUpdate();
      }
    },
    undoConfig() {
      this.waiting = true;
      api.va.__id__.undo_config(this.id).then(this.handleGetConfig());
    },
    redoConfig() {
      this.waiting = true;
      api.va.__id__.redo_config(this.id).then(this.handleGetConfig());
    },
    handleInit() {
      // console.log(`configure.handleInit() id=${this.id}`);
      this.previous_id = this.id;

      // console.log(this.$store.getters["analyzers/isValidId"](this.id));

      // Check if this.id is queued. If not, navigate to /
      // if (this.$store.getters["analyzers/isValidId"](this.id) === false) {
      if (this.$store.getters["analyzers/getIndex"](this.id) === -1) {
        this.$router.push(`/`);
      } else {
        // console.log("initializing");
        this.$root.$emit(events.sidebar.open(this.id));

        if (!this.ready.config) {
          this.$store
            .dispatch("analyzers/get_config", { id: this.id })
            .then(() => {
              // console.log("handleInit callback");
              this.handleCheckSchema();
              this.handleGetConfig();
            });
        } else {
          this.handleCheckSchema();
          this.handleGetConfig();
        }
      }
    },
    handleCleanUp() {},
    handleCheckConfig() {
      const ok =
        this.config.hasOwnProperty("features") &&
        this.config.features !== undefined; // this is just the first field that comes up as an error otherwise
      // console.log(`config is ok? ${ok}`);
      this.ready.config = ok;
      return ok;
    },
    handleCheckSchema() {
      const ok =
        this.schema.hasOwnProperty("properties") &&
        this.schema.properties !== undefined;
      // console.log(`schema is ok? ${ok}`);
      this.ready.schema = ok;
      return ok;
    },
    handleGetConfig() {
      // console.log("configure.hangleGetConfig()");

      this.config = this.$store.getters["analyzers/getAnalyzerConfigCopy"](
        this.id
      );
      this.ready.config = this.handleCheckConfig();
      this.waiting = false;

      // console.log(`ready: ${this.ready.config && this.ready.schema}`);
      // console.log(this.ready);

      // console.log("config=");
      // console.log(this.config);
    },
    handleSetConfig() {
      // console.log("configure.handleSetConfig()");
      this.waiting = true;
      this.$store
        .dispatch("analyzers/set_config", {
          id: this.id,
          config: this.config,
        })
        .then(() => {
          this.handleGetConfig();
        });
    },
    handleUpdate: throttle(
      250,
      false,
      debounce(250, false, function () {
        this.handleSetConfig();
      })
    ),
    handleResetToDefaults() {
      this.$store.commit("analyzers/newNotice", {
        id: this.id,
        notice: {
          message: "resetting config to defaults has not been implemented yet!",
        },
      });
    },
  },
  watch: {
    "$route.query.id"() {
      // console.log(`id has changed ${this.id}`);

      // this.$forceUpdate();
      this.handleCleanUp();
      this.handleInit();
    },
    store_config() {
      // console.log("config changed");
      this.handleGetConfig();
    },
    schema() {
      // console.log("schema changed");
      this.ready.schema = this.handleCheckSchema();
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
    store_config() {
      return this.$store.getters["analyzers/getAnalyzerConfig"](this.id);
    },
    isReady() {
      // console.log(
      //   `configure.isReady() ${this.ready.schema && this.ready.config}`
      // );
      return this.ready.schema && this.ready.config;
    },
  },
  data() {
    return {
      ready: {
        schema: false,
        config: false,
      },
      config: {},
      waiting: true,
      out: {
        name: null,
        description: null,
      },
      lastEnter: false,
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
  margin-top: 2px;
  margin-bottom: 4px;
  overflow-y: scroll;
  overflow-x: hidden;
  max-width: calc(100vw - #{$sidebar-width} - 4px);
}

.description-label-row {
  margin-bottom: -5px;
}

.basic-config-container {
  padding: 2px;
  .card-body {
    padding: 0;
  }
}

.basic-config-gap {
  padding-left: 4px;
  padding-top: 4px;
}

.config-spinner {
  font-size: 18px;
  color: theme-color("gray-700");
}

.unclickable * {
  pointer-events: none !important;
}
</style>
