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
                <b-button><i class="fa fa-file-video-o"></i></b-button>
              </b-input-group-prepend>
              <b-form-input
                v-bind:style="formStyle"
                ref="video_path"
                type="text"
                v-model="config.video_path"
              ></b-form-input>
            </b-input-group>
          </b-form-group>
        </b-row>
        <b-row class="card-form-row">
          <b-form-group>
            <b-input-group>
              <b-input-group-prepend>
                <b-button><i class="fa fa-file-code-o"></i></b-button>
              </b-input-group-prepend>
              <b-form-input
                v-bind:style="formStyle"
                ref="design_path"
                type="text"
                v-model="config.design_path"
              ></b-form-input>
            </b-input-group>
          </b-form-group>
        </b-row>
        <b-row class="card-form-row">
          <b-form-group>
            <b-input-group>
              <b-input-group-prepend>
                <b-form-select
                  ref="frame_interval_setting"
                  v-model="config.frame_interval_setting"
                  select="selectFrameIntervalSetting"
                  :plain="false"
                  :options="['Nf', 'dt']"
                  class="frame-interval-selector"
                >
                </b-form-select>
                <b-form-input
                  ref="interval"
                  type="text"
                  v-model="config[`${config.frame_interval_setting}`]"
                  class="interval"
                ></b-form-input>
              </b-input-group-prepend>
              &ensp;
              <b-form-input
                ref="height_mm"
                type="text"
                class="card-config-form"
                v-model="config.height_mm"
              ></b-form-input>
            </b-input-group>
          </b-form-group>
        </b-row>
        <b-row class="card-form-row">
          <b-form-group>
            <b-input-group> </b-input-group>
          </b-form-group>
        </b-row>
      </b-container>
    </b-col>
  </b-row>
</template>

<script>
import { check_files } from "../../assets/api";

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
          video_path: "/home/ybnd/projects/200210 - isimple/data/",
          design_path: "/home/ybnd/projects/200210 - isimple/data/",
          frame_interval_setting: "Nf",
          Nf: 100,
          dt: 5,
          height_mm: 0.153
        };
      }
    }
  },
  methods: {
    getConfig() {
      return {
        video_path: this.config.video_path,
        design_path: this.config.design_path,
        frame_interval_setting: this.config.frame_interval_setting,
        [`${this.config.frame_interval_setting}`]: this.config[
          `${this.config.frame_interval_setting}`
        ],
        height: this.config.height_mm / 1000
      };
    },
    async isComplete() {
      // todo: should separate video & design file validation; highlight the invalid one.
      console.log("Calling `isComplete()`");
      console.log(`Video: ${this.config.video_path}`);
      console.log(`Design: ${this.config.design_path}`);
      return check_files([
        this.$refs.video_path.value,
        this.$refs.design_path.value
      ]).then(ok => {
        return ok;
      });
    }
  },
  data() {
    return {
      output: {}
    };
  }
};
</script>

<style scoped>
/*text-align: left;*/
.column-container {
  margin-top: -15px;
  margin-left: -16px;
  padding-right: 3px;
  margin-bottom: -37px;
  vertical-align: bottom;
}
.card-form-row {
  margin-top: -10px;
  margin-bottom: -10px;
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
</style>
