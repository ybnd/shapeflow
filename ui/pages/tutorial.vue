<template>
  <div class="fixed-page">
    <WebpackMarkdown :raw_content="raw_content" />
  </div>
</template>

<script>
import WebpackMarkdown from "../components/WebpackMarkdown";

export default {
  name: "tutorial",
  components: { WebpackMarkdown },
  data() {
    return {
      raw_content: markdown.tutorial
    };
  }
};
</script>

<style></style>
