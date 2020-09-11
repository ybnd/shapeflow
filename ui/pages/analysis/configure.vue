<template>
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button
          class="header-button-icon"
          data-toggle="tooltip"
          title="Reset to defaults (DOES NOTHING FOR NOW)"
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
              @change="handleUpdate"
            ></b-form-input>
          </b-input-group>
        </b-row>
        <b-row class="isimple-form-row description-row">
          <b-input-group class="isimple-form-group">
            <!--todo: not flushed properly when switching analyzers-->
            <b-form-textarea
              class="isimple-form-field-text description-box"
              v-model.lazy="config.description"
              placeholder="add a description here"
              @change="handleUpdate"
            ></b-form-textarea>
          </b-input-group>
        </b-row>
      </b-card>
      <b-card class="basic-config isimple-form-section">
        <BasicConfig
          ref="BasicConfig"
          :config="config"
          :static-paths="true"
          @change="handleUpdate"
        />
      </b-card>
      <b-card
        class="isimple-form-section advanced-config-box advanced-config-collapse"
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
          v-if="config"
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
          @input="handleUpdate"
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

import { undo_config, redo_config } from "../../static/api";

import { events } from "../../static/events";

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
        this.handleGetConfig();
      }
    },
    handleCleanUp() {},
    handleGetConfig() {
      console.log("configure.hangleGetConfig()");

      this.config = this.$store.getters["analyzers/getAnalyzerConfigCopy"](
        this.id
      );

      // console.log("config=");
      // console.log(this.config);
    },
    handleSetConfig() {
      // send config to backend
      this.$store
        .dispatch("analyzers/set_config", {
          id: this.id,
          config: this.config,
        })
        .then(() => {
          this.config = this.$store.getters["analyzers/getAnalyzerConfigCopy"](
            this.id
          );
        });
    },
    handleUpdate: throttle(
      250,
      false,
      debounce(250, false, function () {
        this.handleSetConfig();
      })
    ),
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
</style>
