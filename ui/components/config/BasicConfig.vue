<template>
  <b-row>
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
    <b-col>
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
                v-bind:class="{
                  'is-valid': validVideo,
                  'is-invalid': invalidVideo
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
                  'is-invalid': invalidDesign
                }"
              ></b-form-input>
            </b-input-group>
          </b-form-group>
        </b-row>
        <b-row class="card-form-row">
          <b-form-group>
            <b-input-group>
              <b-form-select
                ref="frame_interval_setting"
                v-model="config.frame_interval_setting"
                @change="selectFrameIntervalSetting"
                :plain="false"
                :options="frame_interval_setting_options"
                class="frame-interval-selector"
              >
              </b-form-select>
              <b-form-input
                ref="interval"
                type="text"
                v-model="config[`${config.frame_interval_setting}`]"
                class="interval"
              ></b-form-input>
            </b-input-group>
          </b-form-group>
          <b-form-group>
            <b-input-group>
              <b-form-select
                ref="feature_setting"
                v-model="config.feature"
                @change="selectFeature"
                :plain="false"
                :options="feature_options"
                class="feature-selector"
              >
              </b-form-select>
              <b-form-input
                ref="height_mm"
                type="text"
                class="card-config-form"
                v-bind:class="{
                  hidden: !showHeight
                }"
                v-model="config.height_mm"
              ></b-form-input>
            </b-input-group>
          </b-form-group>
        </b-row>
      </b-container>
    </b-col>
  </b-row>
</template>

<script>
import {
  select_design_path,
  select_video_path,
  check_design_path,
  check_video_path,
  get_options,
  resolve_paths
} from "../../static/api";

import AsyncComputed from "vue-async-computed";
import Vue from "vue";

Vue.use(AsyncComputed);

export default {
  name: "BasicConfig",
  props: {
    formStyle: {
      type: Object,
      default() {
        return {};
      }
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
          feature: "Volume_uL",
          height_mm: 0.153
        };
      }
    }
  },
  methods: {
    getConfig() {
      return Object.assign(this.config, {
        [`${this.config.frame_interval_setting}`]: this.config[
          `${this.config.frame_interval_setting}`
        ],
        height: this.config.height_mm / 1000,
        height_mm: undefined
      });
    },
    selectFrameIntervalSetting(setting) {
      if (setting in this.frame_interval_setting_options) {
        console.log("selecting frame_interval_setting");
        console.log(setting);
        this.config.frame_interval_setting = setting;
      }
    },
    selectFeature(feature) {
      if (feature in this.feature_options) {
        console.log("selecting feature");
        console.log(feature);
        this.config.feature = feature;
        this.showHeight = "h" in this.feature_parameters[feature];
      }
    },
    selectVideoFile() {
      select_video_path().then(path => {
        if (path) {
          this.config.video_path = path;
        }
      });
    },
    selectVideoFileFromDropdown(path) {
      console.log(`selectVideoFileFromDropdown: ${path}`);
      if (path) {
        this.config.video_path = path;
      }
    },
    selectDesignFile() {
      select_design_path().then(path => {
        if (path) {
          this.config.design_path = path;
        }
      });
    },
    selectDesignFileFromDropdown(path) {
      console.log(`selectDesignFileFromDropdown: ${path}`);
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
      return check_video_path(this.config.video_path).then(ok => {
        this.validVideo = ok;
        this.invalidVideo = !ok;
        return ok;
      });
    },
    async checkDesignPath() {
      return check_design_path(this.config.design_path).then(ok => {
        this.validDesign = ok;
        this.invalidDesign = !ok;
        return ok;
      });
    }
  },
  beforeMount() {
    this.selectFeature(this.config.feature);
    this.selectFrameIntervalSetting(this.config.frame_interval_setting);
  },
  asyncComputed: {
    feature_parameters: {
      async get() {
        return get_options("feature").then(options => {
          return options;
        });
      },
      default: []
    },
    feature_options: {
      async get() {
        return get_options("feature").then(options => {
          console.log("got feature options object");
          console.log(options);
          return Object.keys(options);
        });
      },
      default: []
    },
    frame_interval_setting_options: {
      async get() {
        return get_options("frame_interval_setting").then(options => {
          return options;
        });
      },
      default: []
    },
    video_path_options: {
      async get() {
        return get_options("video_path").then(options => {
          console.log(options);
          this.config.video_path = options[0];
          return options;
        });
      },
      default: []
    },
    design_path_options: {
      async get() {
        return get_options("design_path").then(options => {
          console.log(options);
          this.config.design_path = options[0];
          return options;
        });
      },
      default: []
    }
  },
  data() {
    return {
      showHeight: false,
      validVideo: false,
      invalidVideo: false,
      validDesign: false,
      invalidDesign: false,
      frame_interval_setting_options: [],
      feature_options: [],
      video_path_options: [],
      design_path_options: []
    };
  }
};
</script>

<style scoped>
.column-container {
  margin-top: -15px;
  margin-left: -16px;
  padding-right: 3px;
  vertical-align: bottom;
}
.card-form-row {
  margin-bottom: 8px;
  height: 30px;
  max-height: 30px;
}
.card-config-form {
  max-width: 140px;
}
.frame-interval-selector {
  margin-right: 4px;
}
.interval {
  width: 86px;
}
.hidden {
  visibility: hidden;
}
</style>
