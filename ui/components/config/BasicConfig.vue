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
              ><i class="fa fa-file-video-o"></i
            ></b-button>
            <b-dropdown
              text=""
              data-toggle="tooltip"
              title="Recent video files"
            >
              <b-dropdown-item
                v-for="path in video_path_options"
                :key="`path-${path}`"
                @click="selectVideoFileFromDropdown(path)"
              >
                {{ path }}
              </b-dropdown-item>
            </b-dropdown>
          </b-input-group-prepend>
          <b-form-input
            v-bind:style="formStyle"
            ref="video_path"
            type="text"
            v-model="config.video_path"
            class="path-form"
            v-bind:class="{
              'is-valid': validVideo,
              'is-invalid': invalidVideo,
            }"
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
              ><i class="fa fa-file-code-o"></i
            ></b-button>
            <b-dropdown
              text=""
              data-toggle="tooltip"
              title="Recent design files"
            >
              <b-dropdown-item
                v-for="path in design_path_options"
                :key="`path-${path}`"
                @click="selectDesignFileFromDropdown(path)"
              >
                {{ path }}
              </b-dropdown-item>
            </b-dropdown>
          </b-input-group-prepend>
          <b-form-input
            v-bind:style="formStyle"
            ref="design_path"
            type="text"
            v-model="config.design_path"
            v-bind:class="{
              'is-valid': validDesign,
              'is-invalid': invalidDesign,
            }"
          ></b-form-input>
        </b-input-group>
      </b-form-group>
    </b-row>
    <b-row class="card-form-row">
      <b-input-group-text class="leftmost-text">
        <b>Frames</b>
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
          ></b-form-input>
        </b-input-group>
      </b-form-group>
    </b-row>

    <template v-for="(feature, index) in config.features">
      <b-row class="feature-row" v-bind:key="`row-${index}`">
        <b-col class="feature-col" v-bind:key="`feature-col-${index}`">
          <b-form-row
            class="feature-row"
            v-bind:key="`feature-col-row-${index}`"
          >
            <b-input-group
              ><b-input-group-text class="leftmost-text">
                <template v-if="index === 0"> <b>Features</b></template>
                <template v-else></template>
              </b-input-group-text>
              <b-form-select
                ref="feature_setting"
                v-bind:key="`form-feature-${feature}`"
                v-model="config.features[index]"
                @change="selectFeature"
                :plain="false"
                :options="features.options"
                class="feature-selector"
            /></b-input-group>
          </b-form-row>
        </b-col>

        <b-col class="par-col" v-bind:key="`par-col-${feature}`">
          <b-form-row class="feature-row" v-bind:key="`par-col-row-${feature}`"
            ><b-form-group>
              <b-input-group>
                <template v-for="parameter in features.parameters[feature]">
                  <b-input-group-text
                    v-bind:key="`form-text-${index}-${parameter}`"
                  >
                    {{ features.parameter_descriptions[feature][parameter] }}
                  </b-input-group-text>
                  <b-form-input
                    type="text"
                    class="config-form"
                    :value="
                      hasParameterData(feature, parameter)
                        ? config.parameters[feature][parameter]
                        : features.parameter_defaults[feature][parameter]
                    "
                    v-bind:key="`form-field-${index}-${parameter}`"
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
          <b-input-group-text class="add-feature" @click="handleAddFeature">
            <i class="fa fa-plus" />
            <div class="add-feature-text">
              &nbsp; Add feature...
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

import _ from "lodash";

Vue.use(AsyncComputed);

export default {
  name: "BasicConfig",
  props: {
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
          video_path: "/home/ybnd/projects/200210 - isimple/data/shuttle.mp4",
          design_path: "/home/ybnd/projects/200210 - isimple/data/shuttle.svg",
          frame_interval_setting: "Nf",
          Nf: 100,
          dt: 5,
          features: ["Volume_uL"],
          parameters: {},
        };
      },
    },
  },
  methods: {
    hasParameterData(feature, parameter) {
      if (_.has(this.config.parameters, feature)) {
        return _.has(this.config.parameters[feature], parameter);
      }
    },
    getConfig() {
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
    },
    handleRemoveFeature(index) {
      this.config.features.splice(index, 1);
    },
    handleAddFeature() {
      this.config.features = [
        ...this.config.features,
        this.features.options[0],
      ];
      // console.log(this.config);
    },
    selectFeature(feature) {
      // console.log(`selectFeature(${feature})`);
      // console.log(this.features);
      if (this.features.options.includes(feature)) {
        // console.log("selecting feature");
        // console.log(feature);
        this.config.feature = feature;
      }
    },
    selectVideoFile() {
      select_video_path().then((path) => {
        if (path) {
          this.config.video_path = path;
        }
      });
    },
    selectVideoFileFromDropdown(path) {
      // console.log(`selectVideoFileFromDropdown: ${path}`);
      if (path) {
        this.config.video_path = path;
      }
    },
    selectDesignFile() {
      select_design_path().then((path) => {
        if (path) {
          this.config.design_path = path;
        }
      });
    },
    selectDesignFileFromDropdown(path) {
      // console.log(`selectDesignFileFromDropdown: ${path}`);
      if (path) {
        this.config.design_path = path;
      }
    },
    async hasValidFiles() {
      let video_ok = await this.checkVideoPath();
      let design_ok = await this.checkDesignPath();
      return video_ok && design_ok;
    },
    async checkVideoPath() {
      return check_video_path(this.config.video_path).then((ok) => {
        this.validVideo = ok;
        this.invalidVideo = !ok;
        return ok;
      });
    },
    async checkDesignPath() {
      return check_design_path(this.config.design_path).then((ok) => {
        this.validDesign = ok;
        this.invalidDesign = !ok;
        return ok;
      });
    },
  },
  watch: {
    features() {
      // for any features that we don't have values for, set defaults
      for (let i = 0; i < features.options.length; i++) {
        if (!(features.options[i] in this.config.parameters)) {
          this.config.parameters = {
            ...this.config.parameters,
            [features.options[i]]:
              features.parameter_defaults[features.options[i]],
          };
        }
      }
      if (this.features.options !== undefined) {
        this.selectFeature(this.config.feature);
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
      return this.$store.state.options.feature;
    },
    frame_interval_settings() {
      return this.$store.state.options.frame_interval_setting;
    },
  },
  asyncComputed: {
    video_path_options: {
      async get() {
        return get_options("video_path").then((options) => {
          // console.log(options);

          if (!this.config.video_path) {
            this.config.video_path = options[0];
          }

          return options;
        });
      },
      default: [],
    },
    design_path_options: {
      async get() {
        return get_options("design_path").then((options) => {
          // console.log(options);

          if (!this.config.design_path) {
            this.config.design_path = options[0];
          }

          return options;
        });
      },
      default: [],
    },
  },
  data() {
    return {
      showHeight: false,
      validVideo: false,
      invalidVideo: false,
      validDesign: false,
      invalidDesign: false,
      video_path_options: [],
      design_path_options: [],
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
