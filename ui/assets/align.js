export function roiRectInfoToCoordinates(rect, frame) {
  // convert absolute moveable RectInfo to relative coordinates {TL, TR, BL, BR}
  //   -> RdctInfo: https://daybrush.com/moveable/release/latest/doc/Moveable.html#.RectInfo
  return {
    TL: {
      x: (rect.pos1[0] - rect.left) / frame.width,
      y: rect.pos1[1] / frame.height
    },
    TR: {
      x: (rect.pos2[0] - rect.left) / frame.width,
      y: rect.pos2[1] / frame.height
    },
    BL: {
      x: (rect.pos3[0] - rect.left) / frame.width,
      y: rect.pos3[1] / frame.height
    },
    BR: {
      x: (rect.pos4[0] - rect.left) / frame.width,
      y: rect.pos4[1] / frame.height
    }
  };
}

export function roiCoordinatesToTransform(coordinates, frame) {
  // convert relative coordinates [TL, TR, BL, BR] to CSS matrix3d...
}
