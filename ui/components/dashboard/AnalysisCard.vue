<template>
  <b-card show-footer class="analysis-card">
    <b-row>
      <b-col> <!-- todo: would be cool to have a triangl/triangle combo thumbnail that reveals the video/design fully on hover-->
        <div class="thumbnail column-container">
          <b-img fluid-grow :src="`/api/analyzer/thumbnail-design/${id}`"/>  <!-- todo: connect to file input instead: https://stackoverflow.com/questions/49106045 -->
        </div>
      </b-col>
      <b-col>
        <div class="thumbnail column-container">
          <b-img fluid-grow :src="`/api/analyzer/thumbnail-design/${id}`"/>
        </div>
      </b-col>
      <b-col>
        <b-container class="column-container">
          <b-row class="card-form-row">
            <b-form-group>
              <b-input-group class="popover-field">
                <b-input-group-prepend>
                  <b-button><i class="fa fa-file-video-o"></i></b-button>
                </b-input-group-prepend>
                <b-form-input class="form-width-setter" id="video_path" type="text" :value="config['video_path']" ></b-form-input>
              </b-input-group>
            </b-form-group>
          </b-row>
          <b-row class="card-form-row">
            <b-form-group>
              <b-input-group >
                <b-input-group-prepend>
                  <b-button><i class="fa fa-file-code-o"></i></b-button>
                </b-input-group-prepend>
                <b-form-input class="form-width-setter" id="design_path" type="text" :value="config['design_path']"></b-form-input>
              </b-input-group>
            </b-form-group>
          </b-row>
          <b-row class="card-form-row">

            <b-form-group>
              <b-input-group>
                <b-input-group-prepend>
                  <b-form-select id="frame_interval_setting"
                                 :value="config['frame_interval_setting']"
                                 select="selectFrameIntervalSetting"
                                 :plain="false"
                                 :options="['Nf', 'dt']"
                                 class="frame-interval-selector">
                  </b-form-select>
                  <b-form-input
                    id="interval" type="text" :value="config['interval']" class="interval"></b-form-input>
                </b-input-group-prepend>
                &ensp;
                <b-form-input id="height" type="text" class="card-config-form" :value="config['height']"></b-form-input>
              </b-input-group>
            </b-form-group>
          </b-row>
          <b-row class="card-form-row">
            <b-form-group>
              <b-input-group>
              </b-input-group>
            </b-form-group>
          </b-row>
        </b-container>
      </b-col>
    </b-row>
    <div slot="footer" class="handle">
      <b-input-group>
        <b-input-group-prepend>
          <b-button>#{{index+1}}</b-button>
        </b-input-group-prepend>
        <b-form-input id="name" type="text" :value="name" class="card-name-form"></b-form-input>
      </b-input-group>
    </div>
  </b-card>
</template>

<script>
export default {
  props: {
    name: {
      type: String,
      default: ''
    },
    id: {
      type: String,
      default: ''
    },
    index: {
      type: Number,
      default: 0,
    },
    progress: {
      type: Number,
      default: 0,
    },
    state: {
      type: String,
      enum: ['incomplete', 'ready', 'running', 'done', 'canceled', 'error'],
      default: 'incomplete',
    },
    config: {
      type: Object,
      default: () => {
        return {
          video_path: '',
          design_path: '',
          frame_interval_setting: '',
          interval: '',
          height: '',
        };
      }
    },
  },
  data() {
    return {
      show: false,
      selected: 'dt',  // todo: this means that the default value is always reset; we should go by the history though!
      interval_placeholder: {
        'Nf': '# frames',     // todo: this works when `selected`is changed here, but I'm not sure how to make it resolve on click...
        'dt': 'interval (s)',
      }
    }
  },
};

</script>

<style scoped>
.analysis-card {
  /*text-align: left;*/
  max-width: 800px;
  max-height: 400px;
  min-height: 160px;
  display: flex !important;
  flex-direction: column !important;
  flex-wrap: wrap !important;
  margin: 5px 5px 0 0;
}
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
.card-name-form {
  margin-left: -3px;
  max-width: 160px;
}
.handle {
  margin-left: -16px;
  margin-top: -8px;
  height: 26px;
}
.thumbnail {
  min-height: 60px;
  min-width: 100px;
  max-height: 100px;
  max-width: 178px;
}
</style>
