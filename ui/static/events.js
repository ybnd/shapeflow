export let events = {
  seek(analyzer_id) {
    return `seek-${analyzer_id}`;
  },
  step_forward(analyzer_id) {
    return `step-forward-${analyzer_id}`;
  },
  step_backward(analyzer_id) {
    `step-backward-${analyzer_id}`;
  },
  sidebar: {
    remove(analyzer_id) {
      return `sidebar-remove-${analyzer_id}`;
    },
    cancel(analyzer_id) {
      return `sidebar-cancel-${analyzer_id}`;
    },
    open(analyzer_id) {
      return `sidebar-open-${analyzer_id}`;
    },
    highlight(link_id) {
      return `sidebar-highlight-${link_id}`;
    },
    unhighlight(link_id) {
      return `sidebar-unhighlight-${link_id}`;
    }
  }
};
