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
    <b-row class="card-form-row">
      <b-input-group-text class="leftmost-text">
        <b>Feature</b>
      </b-input-group-text>
      <b-form-group>
        <b-input-group>
          <b-form-select
            ref="feature_setting"
            v-model="config.feature"
            @change="selectFeature"
            :plain="false"
            :options="features.options"
            class="feature-selector"
          >
          </b-form-select>
          <template v-for="parameter in features.parameters[config.feature]">
            <b-input-group-text v-bind:key="`form-text-${parameter}`">
              {{ features.parameter_descriptions[config.feature][parameter] }}
            </b-input-group-text>
            <b-form-input
              type="text"
              class="config-form"
              v-model="config.parameters[config.feature][parameter]"
              v-bind:key="`form-field-${parameter}`"
            >
            </b-form-input>
          </template>
        </b-input-group>
      </b-form-group>
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
          parameters: {}
        };
      }
    }
  },
  methods: {
    getConfig() {
      return Object.assign(this.config, {
        [`${this.config.frame_interval_setting}`]: Number(
          this.config[`${this.config.frame_interval_setting}`]
        ),
        features: [this.config.feature], // todo: temporary - only handling one feature at a time for now
        feature: undefined
      });
    },
    selectFrameIntervalSetting(setting) {
      if (setting in this.frame_interval_settings) {
        console.log("selecting frame_interval_setting");
        console.log(setting);
        this.config.frame_interval_setting = setting;
      }
    },
    selectFeature(feature) {
      console.log(`selectFeature(${feature})`);
      console.log(this.features);
      if (this.features.options.includes(feature)) {
        console.log("selecting feature");
        console.log(feature);
        this.config.feature = feature;
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
  watch: {
    features() {
      if (this.features.options !== undefined) {
        this.selectFeature(this.config.feature);
      }
    },
    frame_interval_settings() {
      try {
        this.selectFrameIntervalSetting(this.config.frame_interval_setting);
      } catch (err) {
        console.log(err);
      }
    }
  },
  asyncComputed: {
    features: {
      async get() {
        return get_options("feature").then(features => {
          this.config.parameters = features.parameter_defaults;
          return features;
        });
      },
      default: {
        options: [],
        descriptions: {},
        parameters: {},
        parameter_defaults: {},
        parameter_descriptions: {}
      }
    },
    frame_interval_settings: {
      async get() {
        return get_options("frame_interval_setting").then(options => {
          console.log(options);
          return options;
        });
      },
      default: {
        options: [],
        descriptions: {}
      }
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
      frame_interval_settings: {
        options: [],
        descriptions: {}
      },
      features: {
        options: [],
        descriptions: {},
        parameters: {},
        parameter_defaults: {},
        parameter_descriptions: {}
      },
      video_path_options: [],
      design_path_options: [],
      frame_interval_setting_text: {
        Nf: "# of equally spaced frames",
        dt: "frame interval (s)"
      }
    };
  }
};
</script>

<style scoped>
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
  min-width: 200px;
  /*max-width: 400px;*/
}
.input-group {
  flex-direction: row;
  flex-shrink: 1;
  flex-grow: 1;
  flex-wrap: nowrap;
}
.config-form {
  min-width: 60px;
  max-width: 140px;
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
}
.feature-selector {
  min-width: 160px;
  max-width: 160px;
  padding: 0;
  margin-right: 5px;
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
