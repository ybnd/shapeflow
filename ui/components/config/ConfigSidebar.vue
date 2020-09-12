<template>
  <div class="config-sidebar">
    <SchemaForm
      v-if="config"
      :data="config"
      :schema="schema"
      :skip="skip"
      class="config-form-container"
      :property_as_title="true"
      @input="handleUpdate"
    />
  </div>
</template>

<script>
import SchemaForm from "../../components/config/SchemaForm";

import cloneDeep from "lodash/cloneDeep";
import { throttle, debounce } from "throttle-debounce";
import { events } from "static/events";

export default {
  name: "ConfigSidebar",
  components: { SchemaForm },
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
  beforeMount() {
    this.handleInit();
  },
  beforeDestroy() {
    this.handleCleanUp();
  },
  methods: {
    handleInit() {
      this.handleGetConfig();
    },
    handleCleanUp() {},
    handleGetConfig() {
      console.log("ConfigSidebar.hangleGetConfig()");

      this.config = this.$store.getters["analyzers/getAnalyzerConfigCopy"](
        this.id
      );
    },
    handleSetConfig() {
      console.log("ConfigSidebar.hangleSetConfig()");

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
  computed: {
    schema() {
      return this.$store.getters["schemas/getConfigSchema"];
    },
    store_config() {
      return this.$store.getters["analyzers/getAnalyzerConfig"](this.id);
    },
  },
  watch: {
    store_config: function () {
      this.handleGetConfig();
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
  max-width: $config-sidebar-width;
  min-width: $config-sidebar-width;
  float: right;
  height: calc(100vh - #{$header-height});
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
