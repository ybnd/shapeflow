<template>
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button @click="setSettings">Save</b-button>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button @click="restart">Restart backend</b-button>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button @click="clearCache">Clear cache</b-button>
      </PageHeaderItem>
    </PageHeader>
    <b-container class="settings-form-container">
      <b-card>
        <h5>Log</h5>
        <FormSchema ref="form_log" v-model="settings.log" class="form-schema" />
      </b-card>
      <b-card>
        <h5>Cache</h5>
        <FormSchema
          ref="form_cache"
          v-model="settings.cache"
          class="form-schema"
      /></b-card>
      <b-card
        ><h5>Render</h5>
        <FormSchema
          ref="form_render"
          v-model="settings.render"
          class="form-schema"
      /></b-card>
      <b-card
        ><h5>Format</h5>
        <FormSchema
          ref="form_format"
          v-model="settings.format"
          class="form-schema"
      /></b-card>

      <b-card
        ><h5>Database</h5>
        <FormSchema ref="form_db" v-model="settings.db" class="form-schema"
      /></b-card>
    </b-container>
  </div>
</template>

<script>
import {
  settings_schema,
  get_settings,
  set_settings,
  clear_cache,
  restart
} from "../static/api";

import FormSchema from "@formschema/native";

import PageHeader from "../components/header/PageHeader";
import PageHeaderItem from "../components/header/PageHeaderItem";
import PageHeaderSeek from "../components/header/PageHeaderSeek";

export default {
  name: "dashboard",
  components: {
    PageHeader,
    PageHeaderItem,
    PageHeaderSeek,
    FormSchema
  },
  beforeMount() {
    get_settings().then(settings => {
      this.settings = settings;
    });
    settings_schema().then(schema => {
      console.log("got schema");
      console.log(schema);

      // modify schema to add titles
      for (var group in schema.properties) {
        if (schema.properties.hasOwnProperty(group)) {
          for (var field in schema.properties[group].properties) {
            if (schema.properties[group].properties.hasOwnProperty(field)) {
              schema.properties[group].properties[
                field
              ].attrs = this.schema_attrs[group][field];
            }
          }
        }
      }

      console.log("schema is now");
      console.log(schema);

      this.$refs.form_cache.load(schema.properties.cache);
      this.$refs.form_db.load(schema.properties.db);
      this.$refs.form_format.load(schema.properties.format);
      this.$refs.form_log.load(schema.properties.log);
      this.$refs.form_render.load(schema.properties.render);
    });
  },
  methods: {
    setSettings() {
      console.log("try to set settings");
      console.log(this.settings);
      set_settings(this.settings).then(settings => {
        this.settings = settings;
      });
      console.log("got back settings");
      console.log(this.settings);
    },
    restart() {
      restart();
    },
    clearCache() {
      clear_cache();
    }
  },
  data() {
    return {
      settings: {
        cache: {},
        db: {},
        format: {},
        log: {},
        render: {}
      },
      schema_attrs: {
        cache: {
          dir: {
            title: "Cache folder"
          },
          size_limit_gb: {
            title: "Cache size limit (GB)"
          }
        },
        db: {
          path: {
            title: "Database file"
          }
        },
        format: {
          datetime_format: {
            title: "Date/time format"
          },
          datetime_format_fs: {
            title: "Date/time format (filesystem-safe)"
          }
        },
        log: {
          dir: {
            title: "Log folder"
          },
          keep: {
            title: "# of log files to keep"
          },
          lvl_console: {
            title:
              "Logging level - Python console - choose from critical, error, warning, info, debug or vdebug"
          },
          lvl_file: {
            title:
              "Logging level - file / application log - choose from critical, error, warning, info, debug or vdebug"
          },
          path: {
            title: "Log file path"
          }
        },
        render: {
          dir: {
            title: "Render folder"
          }
        }
      }
    };
  }
};
</script>

<style lang="scss">
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
  overflow-x: hidden;
  overflow-y: hidden;
  align-items: flex-start;
  justify-content: flex-start;
  max-height: calc(100vh - #{$header-height});
  max-width: calc(100vw - #{$sidebar-width});
}
</style>
