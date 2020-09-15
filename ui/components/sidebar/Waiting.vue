<template>
  <span>{{ frames[index] }}</span>
</template>

<script>
export default {
  name: "Waiting",
  props: {
    period: {
      type: Number,
      required: false,
      default: 250,
    },
  },
  mounted() {
    this.advance();
    this.interval = setInterval(this.advance, this.period / this.frames.length);
  },
  destroyed() {
    clearInterval(this.interval);
  },
  methods: {
    advance() {
      this.index = (this.index + 1) % this.frames.length;
    },
  },
  data() {
    return {
      index: 0,
      frames: [
        "••• ", //
        " •••",
        "• ••",
        "•• •",
      ],
      interval: null,
    };
  },
};
</script>
