<template>
  <div class="hovertext">
    <div @click="show = true" :class="classList" id="new-analysis">
      <i :class="'fa fa-plus'"></i>
      New analysis...
      <b-popover target="new-analysis" :show.sync="show" placement="right" boundary="viewport" class="new-analysis-popover" container="body">
        <div class="popover-form-container">
          <b-row class="popover-form-row">
            <b-form-group>
              <b-input-group class="popover-field">
                <b-input-group-prepend>
                  <b-button><i class="fa fa-file-video-o"></i></b-button>
                </b-input-group-prepend>
                <b-form-input class="form-width-setter" id="video_path" type="text" placeholder="Select a video file..." ></b-form-input>
              </b-input-group>
            </b-form-group>
          </b-row>
          <b-row class="popover-form-row">
            <b-form-group>
              <b-input-group >
                <b-input-group-prepend>
                  <b-button><i class="fa fa-file-code-o"></i></b-button>
                </b-input-group-prepend>
                <b-form-input class="form-width-setter" id="design_path" type="text" placeholder="Select a design file..."></b-form-input>
              </b-input-group>
            </b-form-group>
          </b-row>
          <b-row class="popover-form-row">
            <b-form-group>
              <b-input-group>
                <b-input-group-prepend>
                  <b-form-select id="frame_interval_setting"
                                 :v-model="selected"
                                 :value="selected"
                                 select="selectFrameIntervalSetting"
                                 :plain="false"
                                 :options="['Nf', 'dt']"
                                 class="frame-interval-selector">
                  </b-form-select>
                  <b-form-input
                    id="interval" type="text" :placeholder="interval_placeholder[selected]" class="interval"></b-form-input>
                </b-input-group-prepend>
                  &emsp;
                <b-form-input id="height" type="text" class="popover-form-height" placeholder="global height (mm)"></b-form-input>
              </b-input-group>
            </b-form-group>
          </b-row>
          <b-row class="popover-form-row">
            <b-form-group>
              <b-input-group>
<!--                <b-form-input id="name" type="text" placeholder="Analysis 7"></b-form-input>-->
                <div class="popover-buttons">
                  <b-button variant="primary" @click="handleNewAnalysis" class="popover-ok">
                    <i class="fa fa-check"/> New analysis
                  </b-button>
                  <b-button variant="danger" @click="show = false" class="popover-cancel">
                    <i class="fa fa-times"/>
                  </b-button>
                </div>
              </b-input-group>
            </b-form-group>
          </b-row>
        </div>
      </b-popover>
    </div>
  </div>
</template>

<script>
  import axios from 'axios'

  export default {
    name: 'sidebar-nav-link',
    props: {

      icon: {
        type: String,
        default: ''
      },
      badge: {
        type: Object,
        default: () => {}
      },
      variant: {
        type: String,
        default: ''
      },
    },
    methods: {
      handleNewAnalysis () {
        this.show = false;
        let response = axios.get('/api/analyzer/init');
        if (response.status === 200) {
          let id = response['data']['id'];
          this.$router.push( `/analysis/align?id=${id}` )
        } else {

        }
      },
      selectFrameIntervalSetting (e) {
        // this.selected = e.target.value;
        console.log('ass');
        console.log(this.selected);
        console.log(this.interval_placeholder[selected]);
      }
    },
    computed: {
      classList () {
        return [
          'nav-link',
          this.linkVariant,
          ...this.itemClasses,
        ]
      },
      linkVariant () {
        return this.variant ? `nav-link-${this.variant}` : ''
      },
      itemClasses () {
        return this.classes ? this.classes.split(' ') : []
      },
      isExternalLink () {
        return this.url.substring(0, 4) === 'http';
      },
      isApiLink () {
        return this.url.substring(0, 4) === '/api';
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
  }
</script>

<style>
  .hovertext .nav-link {
    color: transparent;
  }
  .hovertext:hover .nav-link {}

  .popover-form-container {  /* todo: should be a single component for the dashboard cards & this popover! Then we can recycle a bunch of stuff. */
    padding-top: 13px;
    padding-left: 15px;
    padding-right: 15px;
    margin-bottom: -12px;
  }
  .popover-form-row {
    margin-top: -10px;
    margin-bottom: -10px;
  }
  .popover-form-height {

  }
  .form-width-setter {
    width: 305px;
  }
  .popover {
    max-width: 380px
  }
  .frame-interval-selector {
    margin-right: 4px;
  }
  .interval {
    width: 86px;
  }
  .popover-buttons {
    margin-top: 8px;
  }
  .popover-form-height {
    max-width: 140px;
  }
</style>
