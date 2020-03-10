<template>
  <div class="fixed-page">
    <header>Log</header>
    <p>some log things go here, I guess?</p>
  </div>
</template>

<script>
  import CardLine1ChartExample from '~/components/dashboard/CardLine1ChartExample'
  import CardLine2ChartExample from '~/components/dashboard/CardLine2ChartExample'
  import CardLine3ChartExample from '~/components/dashboard/CardLine3ChartExample'
  import CardBarChartExample from '~/components/dashboard/CardBarChartExample'
  import MainChartExample from '~/components/dashboard/MainChartExample'
  import SocialBoxChartExample from '~/components/dashboard/SocialBoxChartExample'
  import CalloutChartExample from '~/components/dashboard/CalloutChartExample'
  import Callout from '~/components/'

  export default {
    name: 'dashboard',
    components: {
    },
    data: function () {
      return { }
    },
    methods: {

    },
  }
</script>


<style>
  /*@import '../assets/scss/core/_variables';*/
  .fixed-page {
    max-height: 100vh;
    flex-direction: column;
    flex-wrap: nowrap;
    overflow-x: hidden;
    overflow-y: scroll;
    -ms-overflow-style: -ms-autohiding-scrollbar;
    margin-left: -20px;
    margin-right: -30px;
  }
</style>
