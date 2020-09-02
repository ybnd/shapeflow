<template>
  <!--      <b-col>-->
  <!--        &lt;!&ndash; todo: would be cool to have a triangl/triangle combo thumbnail that reveals the video/design fully on hover&ndash;&gt;-->
  <!--        <div class="thumbnail column-container">-->
  <!--          <b-img fluid-grow :src="`/api/roi/thumbnail-design/${id}`" />-->
  <!--          &lt;!&ndash; todo: connect to file input instead: https://stackoverflow.com/questions/49106045 &ndash;&gt;-->
  <!--        </div>-->
  <!--      </b-col>-->
  <!--      <b-col>-->
  <!--        <div class="thumbnail column-container">-->
  <!--          <b-img fluid-grow :src="`/api/roi/thumbnail-design/${id}`" />-->
  <!--        </div>-->
  <!--      </b-col>-->
  <b-container class="column-container">
    <b-row class="card-form-row">
      <b-form-group>
        <b-input-group class="popover-field">
          <b-input-group-prepend>
            <b-button
              @click="selectVideoFile"
              data-toggle="tooltip"
              title="Browse for a video file..."
              :class="{ disabled: staticPaths }"
              ><i class="fa fa-file-video-o"></i
            ></b-button>
            <template v-if="!staticPaths">
              <b-dropdown
                text=""
                data-toggle="tooltip"
                title="Recent video files"
              >
                <b-dropdown-item
                  v-for="path in path_options.video_path"
                  :key="`path-${path}`"
                  @click="selectVideoFileFromDropdown(path)"
                >
                  {{ path }}
                </b-dropdown-item>
              </b-dropdown>
            </template>
          </b-input-group-prepend>
          <b-form-input
            v-bind:style="formStyle"
            ref="video_path"
            type="text"
            v-model="config.video_path"
            class="path-form"
            :readonly="staticPaths"
            v-bind:class="{
              'is-valid': validVideo === true,
              'is-invalid': validVideo === false,
            }"
            @change="checkVideoPath"
          ></b-form-input>
        </b-input-group>
      </b-form-group>
    </b-row>
    <b-row class="card-form-row">
      <b-form-group>
        <b-input-group>
          <b-input-group-prepend>
            <b-button
              @click="selectDesignFile"
              data-toggle="tooltip"
              title="Browse for a design file..."
              :class="{ disabled: staticPaths }"
              ><i class="fa fa-file-code-o"></i
            ></b-button>
            <template v-if="!staticPaths"
              ><b-dropdown
                text=""
                data-toggle="tooltip"
                title="Recent design files"
                :class="{ disabled: staticPaths }"
              >
                <b-dropdown-item
                  v-for="path in path_options.design_path"
                  :key="`path-${path}`"
                  @click="selectDesignFileFromDropdown(path)"
                >
                  {{ path }}
                </b-dropdown-item>
              </b-dropdown></template
            >
          </b-input-group-prepend>
          <b-form-input
            v-bind:style="formStyle"
            ref="design_path"
            type="text"
            v-model="config.design_path"
            :readonly="staticPaths"
            v-bind:class="{
              'is-valid': validDesign === true,
              'is-invalid': validDesign === false,
            }"
            @change="checkDesignPath"
          ></b-form-input>
        </b-input-group>
      </b-form-group>
    </b-row>
    <b-row class="card-form-row">
      <b-input-group-text class="leftmost-text">
        <b>frames</b>
      </b-input-group-text>
      <b-form-group>
        <b-input-group>
          <b-form-select
            ref="frame_interval_setting"
            v-model="config.frame_interval_setting"
            @change="selectFrameIntervalSetting"
            :plain="false"
            :options="frame_interval_settings.options"
            class="config-form"
          >
          </b-form-select>
          <b-input-group-text>
            {{
              frame_interval_settings.descriptions[
                config.frame_interval_setting
              ]
            }}
          </b-input-group-text>

          <b-form-input
            ref="interval"
            type="text"
            v-model="config[`${config.frame_interval_setting}`]"
            class="config-form"
            @change="emitChange"
          ></b-form-input>
        </b-input-group>
      </b-form-group>
    </b-row>

    <template v-for="(feature, index) in config.features">
      <b-row class="feature-row" :key="`row-${index}`">
        <b-col class="feature-col" :key="`feature-col-${index}`">
          <b-form-row class="feature-row" :key="`feature-col-row-${index}`">
            <b-input-group
              ><b-input-group-text class="leftmost-text">
                <template v-if="index === 0"> <b>features</b></template>
                <template v-else></template>
              </b-input-group-text>
              <b-form-select
                ref="feature_setting"
                :key="`form-feature-${feature}`"
                v-model="config.features[index]"
                @input="selectFeature(index)"
                :plain="false"
                :options="features.options"
                class="feature-selector"
            /></b-input-group>
          </b-form-row>
        </b-col>

        <b-col class="par-col" :key="`par-col-${feature}`">
          <b-form-row class="feature-row" :key="`par-col-row-${feature}`"
            ><b-form-group>
              <b-input-group :key="`par-input-group-row-${feature}`">
                <template
                  v-for="(value, parameter) in config.feature_parameters[index]"
                >
                  <b-input-group-text
                    :key="`form-text-${feature}-${parameter}`"
                  >
                    {{ features.parameter_descriptions[feature][parameter] }}
                  </b-input-group-text>
                  <b-form-input
                    type="text"
                    class="config-form"
                    v-model="config.feature_parameters[index][parameter]"
                    :key="`form-field-${feature}-${parameter}`"
                    @change="emitChange"
                  >
                  </b-form-input>
                </template>
                <template v-if="config.features.length > 1">
                  <b-input-group-text
                    class="remove-feature"
                    @click="handleRemoveFeature(index)"
                  >
                    <i class="fa fa-close" />
                  </b-input-group-text>
                </template>
              </b-input-group> </b-form-group
          ></b-form-row>
        </b-col>
      </b-row>
    </template>

    <b-row>
      <b-input-group-text class="leftmost-text"> </b-input-group-text>
      <b-col class="feature-col">
        <b-form-row>
          <b-input-group-text
            class="add-feature"
            @click="handleAddFeature"
            v-bind:class="{
              'is-valid': validFeatures === true,
              'is-invalid': validFeatures === false,
            }"
          >
            <i class="fa fa-plus" />
            <div class="add-feature-text">
              &nbsp; add feature...
            </div>
          </b-input-group-text>
        </b-form-row>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import {
  select_design_path,
  select_video_path,
  check_design_path,
  check_video_path,
  get_options,
  resolve_paths,
} from "../../static/api";

import AsyncComputed from "vue-async-computed";
import Vue from "vue";

import has from "lodash/has";

Vue.use(AsyncComputed);

export default {
  name: "BasicConfig",
  props: {
    staticPaths: {
      type: Boolean,
      default: false,
    },
    formStyle: {
      type: Object,
      default() {
        return {};
      },
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
          feature_parameters: [], // todo: these don't actually get sent to the backend
        };
      },
    },
  },
  mounted() {
    if ("features" in this.config && this.config.features.length === 0) {
      this.handleAddFeature();
    }
  },
  methods: {
    emitChange() {
      this.$emit("change");
    },
    hasParameterData(feature, parameter) {
      console.log(`BasicConfig.hasParameterData(${feature}, ${parameter})`);

      let has_parameter_data = false;
      if (has(this.config.feature_parameters, feature)) {
        has_parameter_data = has(
          this.config.feature_parameters[feature],
          parameter
        );
      }
      return has_parameter_data;
    },
    getConfig() {
      console.log("BasicConfig.getconfig() -- this.config=");
      console.log(this.config);
      return Object.assign(this.config, {
        [`${this.config.frame_interval_setting}`]: Number(
          this.config[`${this.config.frame_interval_setting}`]
        ),
      });
    },
    selectFrameIntervalSetting(setting) {
      if (setting in this.frame_interval_settings) {
        // console.log("selecting frame_interval_setting");
        // console.log(setting);
        this.config.frame_interval_setting = setting;
      }
      this.emitChange();
    },
    handleRemoveFeature(index) {
      this.config.features.splice(index, 1);
      this.validFeatures = this.config.features.length > 0;
      this.emitChange();
    },
    handleAddFeature() {
      const feature = this.features.options[0];

      if (this.config.features === undefined) {
        this.config.features = [];
      }
      if (this.config.feature_parameters === undefined) {
        this.config.feature_parameters = [];
      }

      this.config.features = [...this.config.features, feature];

      try {
        this.config.feature_parameters = [
          ...this.config.feature_parameters,
          JSON.parse(JSON.stringify(this.features.parameter_defaults[feature])),
        ];
      } catch (e) {
        this.config.feature_parameters = [];
      }

      this.validFeatures = this.config.features.length > 0;
      // console.log(this.config);
      this.emitChange();
    },
    selectFeature(index) {
      let feature = this.config.features[index];

      console.log(`selectFeature(${index}) -> feature = ${feature}`);

      if (this.features.options.includes(feature)) {
        // console.log("selecting feature");
        // console.log(feature);
        this.config.feature_parameters[index] = JSON.parse(
          JSON.stringify(this.features.parameter_defaults[feature])
        );
      }
      this.emitChange();
    },
    selectVideoFile() {
      select_video_path().then((path) => {
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
      select_design_path().then((path) => {
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
      this.validFeatures = this.config.features.length > 0;

      // console.log(`BasicConfig.isValid()`);
      // console.log(`this.validVideo = ${this.validVideo}`);
      // console.log(`this.validDesign = ${this.validVideo}`);
      // console.log(`this.validFeatures = ${this.validVideo}`);
      return this.validVideo && this.validDesign && this.validFeatures;
    },
    async checkVideoPath() {
      return check_video_path(this.config.video_path).then((ok) => {
        this.validVideo = ok;
        return ok;
      });
    },
    async checkDesignPath() {
      return check_design_path(this.config.design_path).then((ok) => {
        this.validDesign = ok;
        return ok;
      });
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
    features() {
      return JSON.parse(JSON.stringify(this.$store.state.schemas.feature)); // todo: replace with getter
    },
    frame_interval_settings() {
      return this.$store.state.schemas.frame_interval_setting; // todo: replace with getter
    },
  },
  asyncComputed: {
    path_options: {
      async get() {
        return get_options("paths").then((options) => {
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
      showHeight: false,
      validVideo: null,
      validDesign: null,
      validFeatures: null,
      path_options: {
        video_path: [],
        design_path: [],
      },
      frame_interval_setting_text: {
        Nf: "# of equally spaced frames",
        dt: "frame interval (s)",
      },
    };
  },
};
</script>

<style scoped lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.disabled {
  pointer-events: none;
}

.input-group-text {
  border-radius: 0;
  margin-right: -1px;
}

.column-container {
  padding-right: 3px;
  vertical-align: bottom;
  display: flex;
  flex-direction: column;
}
.card-form-row {
  margin-bottom: 8px;
  height: 30px;
  max-height: 30px;
  display: flex;
  flex-direction: row;
  flex-shrink: 1;
  flex-grow: 1;
  align-content: flex-start;
  min-width: 200px;
  /*max-width: 400px;*/
}

.feature-row {
  margin-bottom: 2px;
  height: 30px;
  max-height: 30px;
  display: flex;
  flex-direction: row;
  flex-shrink: 1;
  flex-grow: 1;
  align-content: flex-start;
  min-width: 200px;
  /*max-width: 400px;*/

  &:hover * {
    visibility: visible;
  }
}
.input-group {
  flex-basis: auto;
  flex-direction: row;
  flex-shrink: 1;
  flex-grow: 1;
  flex-wrap: nowrap;
  align-items: flex-start;
}
.config-form {
  min-width: 60px;
  flex-grow: 0;
  margin-right: 5px;
}
.leftmost-text {
  height: 30px;
  width: 70px;
  justify-content: right;
  padding-right: 0;
  border: hidden;
  background: none;
  display: block;
  flex-shrink: 0;
  flex-grow: 0;
}
.feature-col {
  margin-left: -10px;
  display: block;
  width: 200px;
  margin-right: 4px;
  flex-grow: 0;
}
.par-col {
  margin-left: 200px;
  display: flex;
}
.feature-selector {
  flex-basis: auto;
  min-width: 160px;
  max-width: 160px;
  flex-shrink: 1;
  flex-grow: 0;
}

.remove-feature {
  visibility: hidden;
  height: 33px;
  width: 33px;
  justify-content: center;
  border: transparent;
  background: transparent;
  -webkit-user-select: none; /* Safari */
  -moz-user-select: none; /* Firefox */
  -ms-user-select: none; /* IE10+/Edge */
  user-select: none; /* Standard */
  &:hover {
    /*border: 2px solid theme-color("primary");*/
    background: theme-color("danger");
    cursor: pointer;
  }
  &:hover * {
    color: #ffffff; /* todo: change to theme color */
  }
}

.add-feature {
  margin-bottom: 4px;
  height: 33px;
  border: transparent;
  background: transparent;
  -webkit-user-select: none; /* Safari */
  -moz-user-select: none; /* Firefox */
  -ms-user-select: none; /* IE10+/Edge */
  user-select: none; /* Standard */
  &:hover {
    /*border: 2px solid theme-color("primary");*/
    background: theme-color("gray-500");
    cursor: pointer;
  }
  &:hover * {
    color: #ffffff; /* todo: change to theme color */
  }
  &.is-invalid {
    background: theme-color("danger");
    &:hover {
      background: darken(theme-color("danger"), 5%);
    }
  }
  &.is-invalid * {
    color: #ffffff; /* todo: change to theme color */
  }
}

.add-feature-text {
  color: transparent;
}

.hidden {
  visibility: hidden;
}
.input-group-text {
  padding: 6px;
}
.path-form {
  min-width: 260px;
  max-width: 600px;
  flex-shrink: 1;
  flex-grow: 1;
}
</style>
