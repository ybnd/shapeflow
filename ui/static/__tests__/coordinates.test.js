import {
  roiIsValid,
  rectToCoordinates,
  roiRectInfoToRelativeCoordinates,
  dragEventToRelativeRectangle,
  toAbsolute,
  getInitialTransform
} from "../coordinates";

import {test, describe} from "@jest/globals";


const ROI = {
    BL: { x: 0.2, y: 0.8 },
    TL: { x: 0.2, y: 0.2 },
    TR: { x: 0.8, y: 0.2 },
    BR: { x: 0.8, y: 0.8 },
};

const INVALID_ROIS = [
  {},
  { x: 0.2, y: 0.3 },
  {
    BL: { x: 0.2, y: 0.8 },
    TL: { x: 0.2, y: 0.2 },
    TR: { x: 0.8, y: 0.2 },
  },
  {
    BL: { x: 0.2, y: 0.8 },
    TL: { x: 0.2, y: 0.2 },
    TR: { x: 0.8, y: 0.2 },
    BR: {},
  },
  {
    BL: { x: 0.2, y: 0.8 },
    TL: { x: 0.2, y: 0.2 },
    TR: { x: 0.8, y: 0.2 },
    BR: { x: 0.8, y: undefined },
  },
];

const RELATIVE_RECT = {
  left: 0.2,
  bottom: 0.8,
  top: 0.2,
  right: 0.8,
}

const ABSOLUTE_RECT = { // todo: check x/y correctness & y direction
  pos1: [70, 50], // TL
  pos2: [130, 50], // TR
  pos3: [70, 110], // BL
  pos4: [130, 110], // BR
}

const ABSOLUTE_ROI = {
  BL: { x: 70, y: 110 },
  TL: { x: 70, y: 50 },
  TR: { x: 130, y: 50 },
  BR: { x: 130, y: 110 },
};

const FRAME = {
  width: 100,
  height: 100,
  left: 50,
  bottom: 130,
  top: 30,
  right: 150,
}

const CENTER = {  // todo: naming is confusing, fix in coordinates.js
  x: -50,
  y: -30,
};

const DOWN = {  // ~ BL in ABSOLUTE_RECT
  clientX: 70,
  clientY: 110
}

const UP = { // ~ TR in ABSOLUTE_RECT
  clientX: 130,
  clientY: 50,
}

const UP_INVALID = { // a 10x10 rectangle is too small
  clientX: 80,
  clientY: 120,
}

const FLIPPED_ROI_BUG = {  // todo: this is a bug in coordinates.js; h/v indices should be flipped. Make sure it doesn't break anything!
  BL: { x: 0.8, y: 0.2 },
  TL: { x: 0.8, y: 0.8 },
  TR: { x: 0.2, y: 0.8 },
  BR: { x: 0.2, y: 0.2 },
};


const re_matrix3d = /^matrix3d\((.*)\)$/g;

function _matrix3d_to_array(str) {
  return [...str.matchAll(re_matrix3d)][0][1].split(',').map(v => parseFloat(v)) // todo: this is messy
}


const TRANSFORM = [0.6,0,0,0,0,0.6,0,0,0,0,1,0,-60,-48,0,1]


describe('roiIsValid()', () => {
  test('valid roi', () => {
    expect(roiIsValid(ROI)).toBe(true)
  })

  test('invalid roi', () => {
    for (const roi of INVALID_ROIS)
      expect(roiIsValid(roi)).toBe(false)
  })
});

test('rectToCoordinates()', () => {
  expect(rectToCoordinates(RELATIVE_RECT)).toEqual(ROI)
})

describe('roiRectInfoToRelativeCoordinates()', () => {
  test('with valid frame', () => {
    expect(roiRectInfoToRelativeCoordinates(ABSOLUTE_RECT, FRAME)).toEqual(ROI)
  })
  test('with null frame', () => {
    expect(roiRectInfoToRelativeCoordinates(ABSOLUTE_RECT, null)).toEqual(undefined)
  })
})

describe('dragEventToRelativeRectangle()', () => {
  test('valid drag', () => {
    expect(dragEventToRelativeRectangle(DOWN, UP, FRAME)).toEqual(FLIPPED_ROI_BUG) // todo: fix this
  })
  test('invalid drag', () => {
    expect(dragEventToRelativeRectangle(DOWN, UP_INVALID, FRAME)).toEqual(null)
  })
})

describe('toAbsolute()', () => {
  test('valid', () => {
    expect(toAbsolute(ROI, FRAME, CENTER)).toEqual(ABSOLUTE_ROI)
  })

  test('valid', () => {
    expect(toAbsolute(ROI, null, CENTER)).toEqual(undefined)
  })
})

describe('getInitialTransform', () => {
  test('valid', () => {
    _matrix3d_to_array(getInitialTransform(ROI, FRAME, FRAME)).forEach((x,i) => {
      console.log(i)
      console.log(x)
      console.log(TRANSFORM[i])
      expect(x).toBeCloseTo(TRANSFORM[i])
    })
  })

  test('invalid frame', () => {
    expect(getInitialTransform(ROI, null, null)).toBe(undefined)
  })

  test('invalid roi', () => {
    expect(getInitialTransform(ROI, null, null)).toBe(undefined)
  })
})



