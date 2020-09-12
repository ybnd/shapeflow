<link rel="stylesheet" href="../assets/scss/_custom.scss" />
<template>
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button @click="setSettings">Save settings & restart</b-button>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button @click="clearDb">Clear database ({{ size.db }})</b-button>
        <b-button @click="clearCache">Clear cache ({{ size.cache }})</b-button>
      </PageHeaderItem>
    </PageHeader>
    <div class="scrollable">
      <b-card class="isimple-settings-box isimple-form-section">
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

import { clear_cache, clear_db, get_cache_size, get_db_size } from "static/api";

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
    this.getDiskSize();
    setInterval(this.getDiskSize, 1000);
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
      clear_cache().then(this.getDiskSize);
    },
    clearDb() {
      clear_db().then(this.getDiskSize);
    },
    getDiskSize() {
      get_cache_size().then((size) => (this.size.cache = size));
      get_db_size().then((size) => (this.size.db = size));
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

.isimple-settings-box {
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
