<template>
  <div>
    <template v-if="isApiLink">
      <template v-if="two_stage">
        <div @click="stageTwo = !stageTwo" :class="classList">
          <i :class="icon"></i> {{name}}
          <b-badge v-if="badge && badge.text" :variant="badge.variant">{{badge.text}}</b-badge>
          <b-modal v-model="stageTwo" @ok="doRequest" title="Please confirm">
            Really {{name.toLowerCase()}} {{id}}?
          </b-modal>
        </div>
      </template>
      <template v-else>
        <div @click="doRequest" :class="classList">
          <i :class="icon"></i> {{name}}
          <b-badge v-if="badge && badge.text" :variant="badge.variant">{{badge.text}}</b-badge>
        </div>
      </template>
    </template>
    <template v-else>
      <div @click="doNavigate" :class="classList">
        <i :class="icon"></i> {{name}}
        <b-badge v-if="badge && badge.text" :variant="badge.variant">{{badge.text}}</b-badge>
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
        stageTwo: false
      }
    }
  }
</script>
