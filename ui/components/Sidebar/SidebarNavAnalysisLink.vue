<template>
  <div>
    <template v-if="isApiLink">
      <template v-if="two_stage">
        <div @click="show = !show" :class="classList" :id="id" class="sidebar-analysis-link">
          &ensp;
          <i :class="icon"></i> {{name}}
          <b-badge v-if="badge && badge.text" :variant="badge.variant">{{badge.text}}</b-badge>
          <b-popover :target="id" :show.sync="show" @ok="doRequest" container="body" placement="right" boundary="viewport">
            <b-button variant="primary" @click="doRequest">
              <i class="fa fa-check"/> {{name}}
            </b-button>
            <b-button variant="danger" @click="show = false">
              <i class="fa fa-times"/>
            </b-button>
          </b-popover>
        </div>
      </template>
      <template v-else>
        <div @click="doRequest" :class="classList" class="sidebar-analysis-link">
          &ensp;
          <i :class="icon"></i> {{name}}
        </div>
      </template>
    </template>
    <template v-else>
      <div @click="doNavigate" :class="classList" class="sidebar-analysis-link">
        &ensp;
        <i :class="icon"></i> {{name}}
      </div>
    </template>
  </div>
</template>
template


<script>
  import axios from 'axios'

  export default {
    name: 'sidebar-nav-link',
    props: {
      name: {
        type: String,
        default: ''
      },
      url: {
        type: String,
        default: ''
      },
      id: {
        type: String,
        default: '<NO ID SET>',
      },
      two_stage: {
        type: Boolean,
        default: false,
      },
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
      doNavigate () {
        this.$router.push( this.url )
      },
      doRequest (rl) {
        this.show = false;
        axios.post( this.url )
      },
    },
    computed: {
      classList () {
        return [
          'nav-link',
          this.linkVariant,
          ...this.itemClasses
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
        show: false
      }
    }
  }
</script>

<style>
  .sidebar-analysis-link {
    font-size: 85%;
  }
</style>
