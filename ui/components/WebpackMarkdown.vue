<template>
  <div class="markdown-container">
    <vue-markdown>{{ content }}</vue-markdown>
  </div>
</template>

<script>
import VueMarkdown from "vue-markdown";
import { decodeWebpackString } from "../static/util";

export default {
  name: "WebpackMarkdown",
  components: { VueMarkdown },
  props: {
    raw_content: {
      required: true
    }
  },
  computed: {
    content() {
      return decodeWebpackString(this.raw_content);
    }
  }
};
</script>

<style scoped>
.markdown-container {
  padding: 6px;
}
</style>
