<template>
  <b-card show-footer class="analysis-card">
    This a placeholder analysis card, should be linked to the analyses in the sidebar.
    <div slot="footer"><i class="fa fa-navicon handle"/>&ensp;{{name}}</div>
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
        };
      }
    }
  },
};
</script>

<style scoped>
.analysis-card{
  margin: 10px 5px 10px 0; /**/
  max-height: 600px;
  max-width: 600px;
}
</style>
