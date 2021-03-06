<link rel="stylesheet" href="../assets/scss/_custom.scss" />
<template>
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button
          class="header-button-icon log-button settings-open-root"
          data-toggle="tooltip"
          title="Open root directory"
          @click="handleOpenRoot"
        >
          <i class="fa fa-folder" />
        </b-button>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button class="settings-save" @click="setSettings">Save settings & restart</b-button>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button class="settings-clear-db" @click="clearDb">Clear database</b-button>
        <b-button class="settings-clear-cache" @click="clearCache">Clear cache ({{ size.cache }})</b-button>
      </PageHeaderItem>

    </PageHeader>
    <div class="scrollable" v-if="settings && schema">
      <b-card class="shapeflow-settings-box shapeflow-form-section">
        <SchemaForm
          :data="settings"
          :schema="schema"
          class="settings-form-container"
          :clickable_categories="false"
          container_class="settings-form-container2"
        />
      </b-card>
    </div>
  </div>
</template>

<script>
import PageHeader from "../components/header/PageHeader";
import PageHeaderItem from "../components/header/PageHeaderItem";
import PageHeaderSeek from "../components/header/PageHeaderSeek";

import SchemaForm from "../components/config/SchemaForm";

import cloneDeep from "lodash/cloneDeep";

import { api } from "../src/api";

export default {
  name: "dashboard",
  components: {
    PageHeader,
    PageHeaderItem,
    PageHeaderSeek,
    SchemaForm,
  },
  mounted() {
    this.$store.dispatch("settings/sync");
    this.getDiskSize();
    setInterval(this.getDiskSize, 1000);
  },
  computed: {
    settings() {
      return this.$store.getters["settings/getSettingsCopy"];
    },
    schema() {
      return this.$store.getters["schemas/getSettingsSchema"];
    },
  },
  methods: {
    setSettings() {
      this.$store.dispatch("settings/set", { settings: this.settings });
    },
    clearCache() {
      api.cache.clear().then(this.getDiskSize);
    },
    clearDb() {
      api.db.forget().then(this.getDiskSize);
    },
    getDiskSize() {
      api.cache.size().then((size) => (this.size.cache = size));
      // get_db_size().then((size) => (this.size.db = size));
    },
    handleOpenRoot() {
      api.fs.open_root().then(ok => {
        if (!ok) {
          this.$store.commit("analyzers/newNotice", {
            notice: { message: "Could not open root directory." },
          });
        }
      })
    }
  },
  data() {
    return {
      size: {
        cache: null,
        db: null,
      },
    };
  },
};
</script>

<style lang="scss" scoped>
$form-element-width: 600px;

@import "../assets/scss/_bootstrap-variables";
@import "../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.scrollable {
  // it's not scrollable tho
  display: flex;
  flex-direction: column;
  max-width: calc(100vw - #{$sidebar-width});
  max-height: calc(100vh - #{$header-height});
  height: calc(100vh - #{$header-height});
  flex-grow: 0;
}

.shapeflow-settings-box {
  margin-top: 2px;
  margin-bottom: 2px;
  overflow-y: scroll;
  overflow-x: hidden;
  //max-width: calc(100vw - #{$sidebar-width} - 4px);
  //-ms-overflow-style: none; //!* IE 11 *!
  //scrollbar-width: none; //!* Firefox 64 *!
}
.settings-form-container {
  margin: 4px;
  padding-bottom: 4px;
}
.settings-form-container2 {
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: row;
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
