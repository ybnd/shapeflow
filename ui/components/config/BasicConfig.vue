<template>
  <b-container class="basic-config">
    <!--  FILES  -->
    <b-row
      v-for="file in files"
      :key="file.type"
      class="basic-config-row path-row"
    >
      <b-input-group>
        <b-input-group-prepend class="path-prepend">
          <b-button
            class="path-browse"
            @click="file.browse"
            data-toggle="tooltip"
            :title="`Browse for a ${file.type} file...`"
            :disabled="staticPaths"
          >
            <i :class="file.icon" />
          </b-button>
          <b-dropdown
            class="path-select"
            data-toggle="tooltip"
            :title="`Recent ${file.type} files`"
            :disabled="staticPaths"
          >
            <b-dropdown-item
              v-for="path in path_options[file.model]"
              class="path-dropdown-item"
              :key="`path-${path}`"
              @click="file.select(path)"
            >
              {{ path }}
            </b-dropdown-item>
          </b-dropdown>
        </b-input-group-prepend>
        <b-form-input
          class="path-input"
          :class="{
            // don't set if null
            'is-valid': file.valid === true,
            'is-invalid': file.valid === false,
          }"
          :readonly="staticPaths"
          @change="file.check"
          @focusout="onFocusOut"
          @keyup.enter="onKeyUpEnter"
          :ref="file.model"
          type="text"
          v-model="config[file.model]"
          :placeholder="`${file.type} file path`"
        />
      </b-input-group>
    </b-row>

    <!--    FRAMES   -->
    <b-row class="basic-config-row">
      <b-col class="leftmost-col">
        <b-input-group-text class="leftmost-label">
          <b>frames</b>
        </b-input-group-text>
      </b-col>
      <b-col class="frame-col">
        <b-row class="basic-config-row">
          <b-input-group>
            <b-form-select
              class="fis-selector shapeflow-form-field-auto"
              ref="frame_interval_setting"
              :v-model="config.frame_interval_setting"
              @change="selectFrameIntervalSetting"
              :plain="false"
              :options="frame_interval_settings.options"
            />
            <b-input-group-text class="fis-label basic-config-label shapeflow-form-label">
              {{
                frame_interval_settings.descriptions[
                  config.frame_interval_setting
                ]
              }}
            </b-input-group-text>
            <b-form-input
              class="fis-value shapeflow-form-field-auto"
              ref="interval"
              type="number"
              v-model="config[config.frame_interval_setting]"
              :placeholder="config.frame_interval_setting"
              @change="onChange"
              @focusout="onFocusOut"
              @keyup.enter="onKeyUpEnter"
            />
          </b-input-group>
        </b-row>
      </b-col>
    </b-row>

    <!--    FEATURES   -->
    <b-row
      v-for="(feature, index) in config.features"
      :key="index"
      class="basic-config-row feature-row"
    >
      <b-col class="leftmost-col" :key="index">
        <b-input-group-text v-if="index === 0" class="leftmost-label">
          <b>features</b>
        </b-input-group-text>
      </b-col>
      <b-col class="feature-col">
        <b-row class="basic-config-row">
          <b-form-select
            class="feature-selector shapeflow-form-field-auto"
            v-model="config.features[index]"
            :options="features.options"
            @input="(v) => selectFeature(index, v)"
            :plain="false"
          />
        </b-row>
      </b-col>
      <b-col class="parameter-col">
        <b-row class="basic-config-row">
          <!--          <b-input-group-->
          <!--            v-for="(value, parameter) in config.feature_parameters[feature]"-->
          <!--            :key="parameter"-->
          <!--            class="parameter-group"-->
          <!--          >-->
          <!--            <b-input-group-text class="basic-config-label">-->
          <!--              {{ features.parameters[feature][parameter].description }}-->
          <!--            </b-input-group-text>-->
          <!--            &lt;!&ndash;          todo: connect to schema !!&ndash;&gt;-->
          <!--            <b-form-input-->
          <!--              class="parameter-field"-->
          <!--              ref="interval"-->
          <!--              type="text"-->
          <!--              v-model="config.feature_parameters[feature][parameter]"-->
          <!--            />-->
          <!--          </b-input-group>-->
          <b-input-group
            v-for="(value, parameter) in config.feature_parameters[index]"
            :key="parameter"
            class="parameter-group"
          >
            <b-input-group-text class="parameter-label basic-config-label shapeflow-form-label">
              {{ features.parameters[feature][parameter].description }}
            </b-input-group-text>
            <SchemaField
              :class_="'parameter-field'"
              :type="features.parameters[feature][parameter].type"
              :value="config.feature_parameters[index][parameter]"
              :options="features.parameters[feature][parameter]"
              @commit="(v) => setParameter(index, parameter, v)"
              :new_row="false"
              :style_="{
                'max-width': ['number', 'integer', 'float'].includes(
                  features.parameters[feature][parameter].type
                )
                  ? '60px'
                  : undefined,
              }"
            />
          </b-input-group>
        </b-row>
      </b-col>
      <b-col class="remove-col">
        <b-button
          v-if="config.features.length > 1"
          class="remove-button"
          @click="handleRemoveFeature(index)"
          data-toggle="tooltip"
          :title="`Remove feature '${feature}'`"
        >
          <i class="fa fa-close" />
        </b-button>
      </b-col>
    </b-row>

    <!--    ADD FEATURE-->
    <b-row class="basic-config-row">
      <b-col class="leftmost-col"> </b-col>
      <b-col class="add-feature-col">
        <b-row class="basic-config-row">
          <b-button
            class="add-button"
            @click="handleAddFeature()"
            v-bind:class="{
              'is-valid': hasFeatures === true,
              'is-invalid': hasFeatures === false,
            }"
          >
            <i class="fa fa-plus" /> &nbsp; Add feature...
          </b-button>
        </b-row>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { api } from "../../src/api";

import AsyncComputed from "vue-async-computed";
import Vue from "vue";
import SchemaField from "./SchemaField";

import has from "lodash/has";
import cloneDeep from "lodash/cloneDeep";
import { COMMIT, ENTER_FOCUSOUT_INTERVAL } from "../../src/events";

Vue.use(AsyncComputed);

export default {
  name: "BasicConfig",
  components: {
    SchemaField,
  },
  props: {
    staticPaths: {
      type: Boolean,
      default: false,
    },
    config: {
      type: Object,
      default: () => {
        return {
          video_path: "",
          design_path: "",
          frame_interval_setting: "Nf",
          Nf: 100,
          dt: 5,
          features: [],
          feature_parameters: [],
        };
      },
    },
  },
  mounted() {
    this.$store.dispatch("schemas/sync");
    if (this.config.features === undefined || this.config.features.length === 0) {
      this.handleAddFeature();
    }
  },
  methods: {
    onChange(v) {
      // console.log(this.config);
      this.$emit(COMMIT);
    },
    onKeyUpEnter() {
      this.lastEnter = Date.now();
      this.$emit(COMMIT);
    },
    onFocusOut(e) {
      // console.log(e);
      if (
        Math.abs(Date.now() - this.lastEnter) > ENTER_FOCUSOUT_INTERVAL
      ) {
        this.$emit(COMMIT);
      }
    },
    setParameter(index, parameter, value) {
      // console.log(
      //   `BasicConfig.setParameter() feature=${index} parameter=${parameter}, value=${value}`
      // );
      this.config.feature_parameters[index][parameter] = value;
      this.onChange();
    },
    getConfig() {
      // console.log("BasicConfig.getconfig() -- this.config=");
      // console.log(this.config);

      let config = Object.assign(this.config, {
        [`${this.config.frame_interval_setting}`]: Number(
          this.config[`${this.config.frame_interval_setting}`] // todo: is this really necessary? maybe just gather both.
          //todo: also: see this text -> number conversion, that's why parameters can't be set!
        ),
      });

      // console.log(config);

      return config;
    },
    selectFrameIntervalSetting(setting) {
      // console.log("selecting frame_interval_setting");
      // console.log(setting);
      if (setting in this.frame_interval_settings) {  // todo: this does nothing basically?
        this.config.frame_interval_setting = setting;
      }
      this.onChange();
    },
    handleRemoveFeature(index) {
      this.config.features.splice(index, 1);
      this.onChange();
    },
    handleAddFeature() {
      const feature = this.features.default;

      if (this.config.features === undefined) {
        this.config.features = [];
      }
      if (this.config.feature_parameters === undefined) {
        this.config.feature_parameters = [];
      }

      this.config.features = cloneDeep([...this.config.features, feature]);

      try {
        this.config.feature_parameters = [
          ...this.config.feature_parameters,
          cloneDeep(this.features.defaults[feature]),
        ];
      } catch (e) {
        console.warn(e);
        this.config.feature_parameters = [];
      }
      this.onChange();
    },
    selectFeature(index, feature) {
      // console.log(`selectFeature(${index}) -> feature = ${feature}`);

      if (this.features.options.includes(feature)) {
        // console.log(this.features);

        this.config.feature_parameters[index] = cloneDeep(
          this.features.defaults[feature]
        );
      }
      this.onChange();
    },
    selectVideoFile() {
      api.fs.select_video().then((path) => {
        if (path) {
          this.config.video_path = path;
          this.checkVideoPath();
        }
      });
    },
    selectVideoFileFromDropdown(path) {
      // console.log(`selectVideoFileFromDropdown: ${path}`);
      if (path) {
        this.config.video_path = path;
        this.checkVideoPath();
      }
    },
    selectDesignFile() {
      api.fs.select_design().then((path) => {
        if (path) {
          this.config.design_path = path;
          this.checkDesignPath();
        }
      });
    },
    selectDesignFileFromDropdown(path) {
      // console.log(`selectDesignFileFromDropdown: ${path}`);
      if (path) {
        this.config.design_path = path;
        this.checkDesignPath();
      }
    },
    async isValid() {
      if (this.validVideo === null) {
        await this.checkVideoPath();
      }
      if (this.validDesign === null) {
        await this.checkDesignPath();
      }

      console.log(this.hasFeatures);
      return this.validVideo && this.validDesign && this.hasFeatures;
    },
    async checkVideoPath() {
      if (!this.staticPaths && this.config.video_path) {
        return api.fs.check_video(this.config.video_path).then((ok) => {
          this.validVideo = ok;
          this.onChange();
          return ok;
        });
      } else {
        // don't bother sending a request if empty string
        if (!this.staticPaths) {
          this.validVideo = false;
          this.onChange();
        }
      }
    },
    async checkDesignPath() {
      if (!this.staticPaths && this.config.design_path) {
        return api.fs.check_design(this.config.design_path).then((ok) => {
          this.validDesign = ok;
          this.onChange();
          return ok;
        });
      } else {
        // don't bother sending a request if empty string
        if (!this.staticPaths) {
          this.validDesign = false;
          this.onChange();
        }
      }
    },
  },
  watch: {
    config() {
      // console.log("BasicConfig.watch.config()");
      for (let i = 0; i < this.config.features.length; i++) {
        if (!this.config.feature_parameters[i]) {
          this.config.feature_parameters[i] = JSON.parse(
            JSON.stringify(
              this.features.parameter_defaults[this.config.features[i]]
            )
          );
        }
      }
    },
    frame_interval_settings() {
      try {
        this.selectFrameIntervalSetting(this.config.frame_interval_setting);
      } catch (err) {
        console.warn(err);
      }
    },
  },
  computed: {
    hasFeatures() {
      return this.config.features !== undefined && this.config.features.length > 0;
    },
    frame_interval_settings() {
      return this.$store.getters["schemas/getFrameIntervalSetting"];
    },
    features() {
      return this.$store.getters["schemas/getFeature"];
    },
    files() {
      return [
        {
          model: "video_path",
          type: "video",
          icon: "fa fa-file-video-o",
          browse: this.selectVideoFile,
          select: this.selectVideoFileFromDropdown,
          check: this.checkVideoPath,
          valid: this.validVideo,
        },
        {
          model: "design_path",
          type: "design",
          icon: "fa fa-file-code-o",
          browse: this.selectDesignFile,
          select: this.selectDesignFileFromDropdown,
          check: this.checkDesignPath,
          valid: this.validDesign,
        },
      ];
    },
  },
  asyncComputed: {
    path_options: {
      async get() {
        return api.db.get_recent_paths().then((options) => {
          if (!this.config.video_path) {
            this.config.video_path = options.video_path[0];
            this.checkVideoPath();
          }
          if (!this.config.design_path) {
            this.config.design_path = options.design_path[0];
            this.checkDesignPath();
          }
          return options;
        });
      },
      default: {
        video_path: [],
        design_path: [],
      },
    },
  },
  data() {
    return {
      lastEnter: 0,
      showHeight: false,
      validVideo: null,
      validDesign: null,
      path_options: {
        video_path: [],
        design_path: [],
      },
    };
  },
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

$gap: 4px;

$fit-height: 30px; // should be smaller than form elements

$path-browse-width: 32px;
$path-select-width: 32px;
$path-button-width: calc(#{$path-browse-width} + #{$path-select-width});

$fis-select-width: 60px;
$fis-value-width: 60px;

$feature-selector-width: 160px;
$parameter-field-width: 60px;
$remove-button-width: 24px;
$add-button-width: 120px;

.basic-config {
  padding: 0;
  margin: 0;
  max-width: 100% !important;
}

.basic-config-row {
  padding: 0;
  margin: 0;
  padding-bottom: $gap;
  padding-right: $gap;
}

.path-prepend {
  width: $path-button-width;
  padding-right: 1px;
}

.path-browse {
  width: $path-browse-width;
  border-style: none;
  padding: 0;
  font-size: 16px;
  &:disabled {
    pointer-events: none;
  }
}

.path-select {
  border-style: none;
  ::v-deep .btn {
    width: $path-select-width;
    padding: 0;
    font-size: 16px;
    &:disabled {
      pointer-events: none;
    }
  }
}

.basic-config-row .leftmost-col {
  padding: 0;
  margin: 0;
  max-width: $path-button-width;

  .leftmost-label {
    height: $fit-height;
    width: $path-button-width;
    text-align: right;
    padding-right: $gap;
    padding-left: 0;
    border: hidden;
    background: none;
    display: block;
    flex-shrink: 0;
    flex-grow: 0;
    * {
      text-align: right;
    }
  }
}

.basic-config-row .frame-col {
  padding: 0;
  margin: 0;
  .basic-config-row {
    padding: 0;
  }
}

.basic-config-row .feature-col {
  padding: 0;
  margin: 0;
  max-width: $feature-selector-width;
  margin-right: $gap;

  .basic-config-row {
    padding: 0;
  }

  .feature-selector {
    width: $feature-selector-width;
    padding: $gap;
  }
}

.basic-config-row .parameter-col {
  padding: 0;
  margin: 0;
  .basic-config-row {
    padding: 0;
    .parameter-group {
      width: auto;
      margin-right: $gap;
      margin-bottom: $gap;
    }
    margin-bottom: -$gap; // cancel out the bottom-most layer of .parameter-group
  }
}

.basic-config-row .remove-col {
  padding: 0;
  margin: 0;
  max-width: $remove-button-width;
  .remove-button {
    width: $remove-button-width;
    height: $remove-button-width;
    padding: 0;
    text-align: center;
    font-size: 14px;
    background: transparent;
    border: none;
    pointer-events: all;
    &:hover {
      background: theme-color("danger");
      color: theme-color("gray-100");
      cursor: pointer;
    }
  }
}

.add-button-text {
  //color: transparent;
}

.basic-config-row .add-feature-col {
  padding: 0;
  margin: 0;
  margin-right: $gap;

  .add-button {
    border: none;
    background: transparent;
    color: transparent;
    border-radius: 0;
    padding-left: 8px;
    pointer-events: all;
    -webkit-user-select: none; /* Safari */
    -moz-user-select: none; /* Firefox */
    -ms-user-select: none; /* IE10+/Edge */
    user-select: none; /* Standard */
    &:hover {
      background: theme-color("gray-500");
      color: theme-color("gray-100") !important;
      cursor: pointer;
    }
    &:focus {
      color: theme-color("gray-700");
    }
    &:hover * {
      color: theme-color("gray-100") !important;
    }
    .fa {
      color: theme-color("gray-700");
    }
  }
}

.basic-config-label {
  border-radius: 0;
  margin-right: -1px;
}

.fis-selector {
  padding: $gap;
  padding-left: calc(2 * #{$gap});
  margin-right: $gap;
  max-width: $fis-select-width;
  min-width: $fis-select-width;
}

.fis-value {
  max-width: $fis-value-width;
  -webkit-appearance: none; // no arrows
  -moz-appearance: textfield;
}

.dropdown-menu {
  border-radius: 0;
}

.path-dropdown-item {
  max-width: calc(
    #{$content-width} - 2 * #{$path-browse-width} - 3px
  ) !important; // avoids
  overflow: hidden;
  text-overflow: ellipsis !important;
}
</style>
