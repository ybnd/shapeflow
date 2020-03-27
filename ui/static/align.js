import { lusolve, multiply, norm, subtract } from "mathjs";

export var css_width = 100; // px
export var css_center = css_width / 2;

export var css_coords = {
  BL: { x: -css_center, y: css_center },
  TL: { x: -css_center, y: -css_center },
  TR: { x: css_center, y: -css_center },
  BR: { x: css_center, y: css_center }
};

export var default_relative_coords = {
  BL: { x: 0.2, y: 0.8 },
  TL: { x: 0.2, y: 0.2 },
  TR: { x: 0.8, y: 0.2 },
  BR: { x: 0.8, y: 0.8 }
};

export function roiRectInfoToCoordinates(rect, frame) {
  // convert absolute RectInfo to relative coordinates {BL, TL, TR, BR}
  //   -> RdctInfo: https://daybrush.com/moveable/release/latest/doc/Moveable.html#.RectInfo
  return {
    BL: {
      x: (rect.pos3[0] - frame.left) / frame.width,
      y: rect.pos3[1] / frame.height
    },
    TL: {
      x: (rect.pos1[0] - frame.left) / frame.width,
      y: rect.pos1[1] / frame.height
    },
    TR: {
      x: (rect.pos2[0] - frame.left) / frame.width,
      y: rect.pos2[1] / frame.height
    },
    BR: {
      x: (rect.pos4[0] - frame.left) / frame.width,
      y: rect.pos4[1] / frame.height
    }
  };
}

export function roiCoordinatesToTransform(coordinates, frame) {
  // convert relative coordinates [TL, TR, BL, BR] to CSS matrix3d...
}

// todo: clean up
export function transform(from_obj, to_obj) {
  // convert {{x,y}} to [{xy}] ~ BL, TL, TR, BR

  let order = ["BL", "TL", "TR", "BR"];
  let from = [];
  let to = [];

  for (let i = 0; i < order.length; i++) {
    from = [...from, from_obj[order[i]]];
    to = [...to, to_obj[order[i]]];
  }

  // taken from https://franklinta.com/2014/09/08/computing-css-matrix3d-transforms/
  var A, H, b, h, i, j, k, k_i, l, lhs, ref, rhs;
  console.assert(from.length === (ref = to.length) && ref === 4);
  A = []; // 8x8
  for (i = j = 0; j < 4; i = ++j) {
    A.push([
      from[i].x,
      from[i].y,
      1,
      0,
      0,
      0,
      -from[i].x * to[i].x,
      -from[i].y * to[i].x
    ]);
    A.push([
      0,
      0,
      0,
      from[i].x,
      from[i].y,
      1,
      -from[i].x * to[i].y,
      -from[i].y * to[i].y
    ]);
  }
  b = []; // 8x1
  for (i = k = 0; k < 4; i = ++k) {
    b.push(to[i].x);
    b.push(to[i].y);
  }
  // Solve A * h = b for h
  h = lusolve(A, b);
  h = h.reduce((a, b) => a.concat(b), []); // flatten h (is [[...], [...], ...]
  H = [
    [h[0], h[1], 0, h[2]],
    [h[3], h[4], 0, h[5]],
    [0, 0, 1, 0],
    [h[6], h[7], 0, 1]
  ];
  // Sanity check that H actually maps `from` to `to`
  for (i = l = 0; l < 4; i = ++l) {
    lhs = multiply(H, [from[i].x, from[i].y, 0, 1]);
    k_i = lhs[3];
    rhs = multiply(k_i, [to[i].x, to[i].y, 0, 1]);
    let dhs = subtract(lhs, rhs);
    console.assert(norm(dhs) < 1e-9, "Not equal:", lhs, rhs);
  }
  return H;
}

// todo: clean up
export function toCssMatrix3d(transform) {
  let content = [];
  for (let col = 0; col < 4; col++) {
    // todo: there should be some 'flatten' function; -> flatten(transpose(transform))
    for (let row = 0; row < 4; row++) {
      content = [...content, transform[row][col]];
    }
  }
  return `matrix3d(${content.join(",")})`; // todo: the translation is magix & window size-dependent
  // todo: could set transform, query rect, and get translation ~ position of top left point?
}

export function toAbsolute(relative, frame, center = 0) {
  let absolute = {};

  Object.keys(relative).map(key => {
    absolute[key] = {
      x: relative[key].x * frame.width - center,
      y: relative[key].y * frame.height - center
    };
  });

  return absolute;
}

export function getInitialTransform(roi, frame) {
  let initial_transform = transform(
    css_coords,
    toAbsolute(roi, frame, css_center)
  );

  return toCssMatrix3d(initial_transform);
}

export function getDefaultRoi(frame) {
  return toAbsolute(default_relative_coords, frame, css_center);
}
