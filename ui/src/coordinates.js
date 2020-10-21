import { lusolve, multiply, norm, subtract } from "mathjs";
import assert from "assert";

const _ROI_FIELDS = ["BL", "TL", "TR", "BR"];
const _PNT_FIELDS = ["x", "y"];

export var default_relative_coords = {
  BL: { x: 0.2, y: 0.8 },
  TL: { x: 0.2, y: 0.2 },
  TR: { x: 0.8, y: 0.2 },
  BR: { x: 0.8, y: 0.8 },
};

export function roiIsValid(roi) {
  // todo: this is quick & dirty
  for (let i = 0; i < _ROI_FIELDS.length; i++) {
    if (roi.hasOwnProperty(_ROI_FIELDS[i])) {
      for (let j = 0; j < _PNT_FIELDS.length; j++) {
        if (roi[_ROI_FIELDS[i]].hasOwnProperty(_PNT_FIELDS[j])) {
          if (typeof roi[_ROI_FIELDS[i]][_PNT_FIELDS[j]] !== "number") {
            return false;
          }
        } else {
          return false;
        }
      }
    } else {
      return false;
    }
  }
  return true;
}

export function rectToCoordinates(rect) {
  return {
    BL: {
      x: rect.left,
      y: rect.bottom,
    },
    TL: {
      x: rect.left,
      y: rect.top,
    },
    TR: {
      x: rect.right,
      y: rect.top,
    },
    BR: {
      x: rect.right,
      y: rect.bottom,
    },
  };
}

export function roiRectInfoToRelativeCoordinates(rect, frame) {
  // convert absolute RectInfo to relative coordinates {BL, TL, TR, BR}
  //   -> RdctInfo: https://daybrush.com/moveable/release/latest/doc/Moveable.html#.RectInfo
  try {
    assert(!(frame === null));
    return {
      BL: {
        x: (rect.pos3[0] - frame.left) / frame.width,
        y: (rect.pos3[1] - frame.top) / frame.height,
      },
      TL: {
        x: (rect.pos1[0] - frame.left) / frame.width,
        y: (rect.pos1[1] - frame.top) / frame.height,
      },
      TR: {
        x: (rect.pos2[0] - frame.left) / frame.width,
        y: (rect.pos2[1] - frame.top) / frame.height,
      },
      BR: {
        x: (rect.pos4[0] - frame.left) / frame.width,
        y: (rect.pos4[1] - frame.top) / frame.height,
      },
    };
  } catch {
    console.warn(`roiRectInfoToRelativeCoordinates: frame is null`);
    return undefined;
  }
}

export function clickEventToRelativeCoordinate(event, frame) {
  let x = (event.clientX - frame.left) / frame.width;
  let y = (event.clientY - frame.top) / frame.height;

  if (x < 0) x = 0;
  if (x > 1) x = 1;
  if (y < 0) y = 0;
  if (y > 1) y = 1;

  return {
    x: x,
    y: y,
  };
}

export function dragEventToRelativeRectangle(down, up, frame) {
  const co0 = clickEventToRelativeCoordinate(down, frame);
  const co1 = clickEventToRelativeCoordinate(up, frame);

  const A = Math.abs(co0.x - co1.x) * Math.abs(co0.y - co1.y);

  // Assuming any area smaller than 1% of the frame is an error

  // console.log(`Area is ${A}`);

  if (A > 0.01) {
    const h = [co0.x, co1.x].sort();
    const v = [co0.y, co1.y].sort();

    // console.log(h)
    // console.log(v)

    return {
      BL: { x: h[1], y: v[0] },
      TL: { x: h[1], y: v[1] },
      TR: { x: h[0], y: v[1] },
      BR: { x: h[0], y: v[0] },
    };
  } else {
    console.warn("invalid rectangle");
    return null;
  }
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
      -from[i].y * to[i].x,
    ]);
    A.push([
      0,
      0,
      0,
      from[i].x,
      from[i].y,
      1,
      -from[i].x * to[i].y,
      -from[i].y * to[i].y,
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
    [h[6], h[7], 0, 1],
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

export function toAbsolute(relative, frame, center = { x: 0, y: 0 }) {
  try {
    let absolute = {};

    Object.keys(relative).map((key) => {
      absolute[key] = {
        x: relative[key].x * frame.width - center.x,
        y: relative[key].y * frame.height - center.y,
      };
    });

    return absolute;
  } catch (err) {
    console.warn(err);
    return undefined;
  }
}

export function getCenter(rect) {
  return { x: rect.width / 2, y: rect.height / 2 };
}

export function getInitialTransform(roi, frame, overlay) {
  try {
    let initial_transform = transform(
      rectToCoordinates(overlay),
      toAbsolute(roi, frame, getCenter(overlay))
    );

    return toCssMatrix3d(initial_transform);
  } catch (err) {
    console.warn(err);
    // console.warn("roi = ");
    // console.warn(roi);
    // console.warn("frame = ");
    // console.warn(frame);
    // console.warn("overlay = ");
    // console.warn(overlay);
    return undefined;
  }
}
