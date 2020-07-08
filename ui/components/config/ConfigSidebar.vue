<template>
  <div class="config-sidebar">
    <VueFormJsonSchema
      v-if="config && ui_schema.length > 0"
      v-model="config"
      class="sidebar-form-container"
      :schema="schema"
      :ui-schema="ui_schema"
      :options="{
        validate: false,
        validateOnLoad: false,
        showValidationErrors: true,
        ajv: {
          options: {
            unknownFormats: ['directory-path', 'file-path'], // these get validated by the backend
            format: false,
            verbose: true,
          },
        },
      }"
    />
  </div>
</template>

<script>
import { UiSchema } from "../../static/ui-schema";
import VueFormJsonSchema from "vue-form-json-schema";
import cloneDeep from "lodash/cloneDeep";

import Vue from "vue";
import AsyncComputed from "vue-async-computed";
Vue.use(AsyncComputed);

export default {
  name: "ConfigSidebar",
  components: { VueFormJsonSchema },
  props: {
    hidden: {
      type: Boolean,
      required: true,
    },
    id: {
      type: String,
      required: true,
    },
    skip: {
      type: Array,
      required: false,
      default() {
        return [
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
          "transform",
        ];
      },
    },
  },
  mounted() {
    this.$store
      .dispatch("analyzers/refresh", { id: this.id })
      .then(this.initConfig());
  },
  methods: {
    initConfig() {
      this.config = cloneDeep(
        this.$store.getters["analyzers/getAnalyzerConfig"](this.id)
      );
      console.log("this.config = ");
      console.log(this.config);
    },
    handleSetConfig() {
      this.$store.dispatch("analyzers/set_config", {
        id: this.id,
        config: this.config,
      });
    },
  },
  computed: {
    schema() {
      return this.$store.getters["schemas/getConfigSchema"];
    },
  },
  asyncComputed: {
    ui_schema: {
      async get() {
        if (this.config !== undefined && this.schema !== undefined) {
          const ui_schema = UiSchema(this.schema, this.config, this.skip);
          // console.log("this.schema = ");
          // console.log(this.schema);
          // console.log("this.ui_schema = ");
          // console.log(JSON.stringify(this.ui_schema));
          return ui_schema;
        } else {
          return [];
        }
      },
      default: [],
    },
  },
  data() {
    return {
      config: {},
      ui_schema: [],
    };
  },
};
</script>

<style lang="scss" scoped>
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.config-sidebar {
  background: #ffffff;
  width: $config-sidebar-width;
  float: right;
  max-height: calc(100vh - #{$header-height});
  overflow-y: scroll;
  overflow-x: hidden;
  -ms-overflow-style: none; /* IE 11 */
  scrollbar-width: none; /* Firefox 64 */
}
.config-sidebar::-webkit-scrollbar {
  display: none; /* Chrome&Chromium */
}

.sidebar-form-container {
  width: $config-sidebar-width;
}
</style>
