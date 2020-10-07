import {seconds2timestr, uuidv4, get_reference, dereference} from "../util";
import { events } from "../events";

import {test, describe} from "@jest/globals";


const def_0 = '#/definitions/def_0';
const def_1 = '#/definitions/def_1';
const def_2 = '#/definitions/def_2';


const DEF_0 = {
  type: "string",
  default: "..."
};

const DEF_1 = {
  type: "object",
  default: {p
    a: 0, b: 1
  }
};

const DEF_2 = {
  type: "number",
  default: "0"
};

const SCHEMA = {
  properties: {
    prop_0: {
      "$ref": def_0
    },
    prop_1: {
      type: "object",
      allOf: [
        {"$ref": def_1, },
      ]
    },
    prop_2: {
      type: "array",
      items: {
        "$ref": def_2
      },
    },
    prop_4: {
      type: "number",
    }
  },
  definitions: {
    def_0: DEF_0,
    def_1: DEF_1,
    def_2: DEF_2
  }
};

describe('util', () => {
  describe('get_reference', () => {
    test('no reference in empty object', () => {
      expect(get_reference({})).toStrictEqual(undefined)
    })

    test('no reference in schema root', () => {
      expect(get_reference(SCHEMA)).toStrictEqual(undefined)
    })

    test('no reference in simple property', () => {
      expect(get_reference(SCHEMA.properties.prop_4)).toStrictEqual(undefined)
    })

    test('correctly find simple reference', () => {
      expect(get_reference(SCHEMA.properties.prop_0)).toStrictEqual(def_0)
    })

    test('correctly find object reference', () => {
      expect(get_reference(SCHEMA.properties.prop_1)).toStrictEqual(def_1)
    })

    test('correctly find array reference', () => {
      expect(get_reference(SCHEMA.properties.prop_2)).toStrictEqual(def_2)
    })
  });

  describe('dereference', () => {
    test('valid definition', () => {
      expect(dereference(SCHEMA, def_0)).toStrictEqual(DEF_0)
    })

    test('invalid definition', () => {
      expect(() => {dereference(SCHEMA, '#/definitions/def_4')}).toThrow()
    })

    test('undefined definition', () => {
      expect(() => {dereference(SCHEMA, undefined)}).toThrow()
    })
  });

  describe('seconds2timestr', () => {
    test('valid call 1', () => {
      expect(seconds2timestr(50)).toEqual("00:50.0")
    })

    test('valid call 2 ', () => {
      expect(seconds2timestr(123.456)).toEqual("02:03.4")  // we're clipping, not rounding
    })

    test('undefined seconds', () => {
      expect(() => {seconds2timestr(undefined)}).toThrow()
    })

    test('null seconds', () => {
      expect(() => {seconds2timestr(null)}).toThrow()
    })
  })

  test('uuidv4', () => {
    uuidv4()
  })
})

const specifier = 'SOMETHING'

describe('events', () => {
  for (const category in events) {
    if (events.hasOwnProperty(category)) {
      describe(category, () => {
        for (const event in events[category]) {
          if (events[category].hasOwnProperty(event)) {
            test(event, () => {
              expect(events[category][event](specifier)).toContain(specifier)
            })
          }
        }
      })
    }
  }
})
