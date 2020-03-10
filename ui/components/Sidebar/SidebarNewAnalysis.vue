<template>
  <div @click="handleNewAnalysis" :class="classList">
    <i :class="'fa fa-plus'"></i>
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
        let response = axios.get('/api/analyzer/init');
        let id = response['data']['id'];
        this.$router.push( `/analysis/configure?id=${id}` )
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
  }
</script>
