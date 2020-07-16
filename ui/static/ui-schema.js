import assert from "assert";
import pointer from "json-pointer";

import get from "lodash/get";
import pullAll from "lodash/pullAll";

function id(model) {
  return `form-${model}`;
}

const InputComponent = {
  // todo: fill out with fitting Bootstrap components
  // todo: get inspired by BasicConfig layout
  enum(model, options) {
    return {
      component: "b-form-select",
      model: model,
      fieldOptions: {
        on: "input",
        class: "isimple-form-field-auto",
        attrs: {
          options: options.enum_options,
          // id: id(model),
        },
      },
    };
  },
  string(model, options) {
    return {
      component: "b-form-input",
      model: model,
      fieldOptions: {
        on: "input",
        class: "isimple-form-field-input",
        // attrs: { id: id(model) },
      },
    };
  },
  integer(model, options) {
    return {
      component: "b-form-input",
      model: model,
      fieldOptions: {
        attrs: {
          type: "number",
          // id: id(model),
        },
        on: { input: (value) => parseInt(value) },
        class: "isimple-form-field-auto",
        style: {
          "max-width": "90px",
        },
      },
    };
  },
  float(model, options = {}) {
    // todo: not sure how or why this is in schema...
    if (options.step === undefined) {
      options.step = 0.1;
    }

    return {
      component: "b-form-input",
      model: model,
      fieldOptions: {
        attrs: {
          type: "number",
          step: options.step,
          // id: id(model),
        },
        style: {
          "max-width": "180px",
        },
        on: { input: (value) => parseFloat(value) },
        class: "isimple-form-field-auto",
      },
    };
  },
  number(model, options = {}) {
    // todo: not sure how or why this is in schema...
    if (options.step === undefined) {
      options.step = 0.1;
    }

    return {
      component: "b-form-input",
      model: model,
      fieldOptions: {
        attrs: {
          type: "number",
          step: options.step,
          // id: id(model),
        },
        style: {
          width: "90px",
        },
        on: { input: (value) => parseFloat(value) },
        class: "isimple-form-field-auto",
      },
    };
  },
  boolean(model, options) {
    return {
      component: "b-form-checkbox",
      model: model,
      fieldOptions: {
        on: "input",
        class: "isimple-form-field-checkbox",
        attrs: {
          // id: id(model),
        },
      },
    };
  },
};

const getComponent = {
  CATEGORY(title, children) {
    return {
      component: "b-form-group",
      fieldOptions: {
        // class: "isimple-form-section",
      },
      children: [
        {
          component: "details",
          fieldOptions: {
            attrs: { open: "" },
            class: "isimple-form-section-fit",
          },
          children: [
            {
              component: "summary",
              fieldOptions: {
                // class: "isimple-form-row",
                domProps: { innerHTML: title },
              },
            },
            {
              component: "div",
              fieldOptions: {
                class: "isimple-form-indent",
                // props: { id: id(title) },
              },
              children: children,
            },
          ],
        },
      ],
    };
  },
  NESTED_CATEGORY(title, children) {
    return {
      component: "b-form-group",
      fieldOptions: {
        class: "isimple-form-section-fit",
      },
      children: [
        {
          component: "details",
          fieldOptions: {
            attrs: { open: "" },
            class: "isimple-form-section-fit",
          },
          children: [
            {
              component: "summary",
              fieldOptions: {
                // class: "isimple-form-row",
                domProps: { innerHTML: title },
              },
            },
            {
              component: "div",
              fieldOptions: {
                class: "isimple-form-indent",
                // props: { id: id(title) },
              },
              children: children,
            },
          ],
        },
      ],
    };
  },
  ARRAY(title, item_type, items) {
    // todo: deprecated!
    // console.log(`ARRAY() of type=${item_type}`);

    return {
      component: "b-card",
      fieldOptions: {
        class: "isimple-form-section-fit",
        props: {
          header: title,
        },
      },
      children: [
        {
          component: "ul",
          class: "isimple-form-array",
          children: items,
        },
      ],
    };
  },
  FIELD(title, type, model, options) {
    // console.log(`FIELD() for type=${type}`);
    return {
      component: "b-form-row",
      fieldOptions: {
        class: "isimple-form-row",
      },
      children: [
        {
          component: "label",
          fieldOptions: {
            class: "mr-sm-2 isimple-form-label",
            // for: id(model),
            domProps: {
              innerHTML: title,
            },
          },
        },
        {
          ...InputComponent[type](model, options),
        },
      ],
    };
  },
};

const Hardcoded = {
  "#/definitions/Coo"(title, model) {
    return {
      component: "b-row",
      fieldOptions: {
        class: "isimple-form-row",
      },
      children: [
        {
          component: "b-input-group",
          fieldOptions: { class: "isimple-form-group" },
          children: [
            {
              component: "label",
              fieldOptions: {
                class: "mr-sm-2 isimple-form-label",
                domProps: { innerHTML: `${title} (x,y)` },
                style: { width: "60px" },
              },
            },
            {
              ...InputComponent.float([model, "x"].join("."), { step: 1e-24 }),
            },
            {
              component: "div",
              fieldOptions: { class: "isimple-form-gap" },
            },
            {
              ...InputComponent.float([model, "x"].join("."), { step: 1e-24 }),
            },
          ],
        },
      ],
    };
  },
  "#/definitions/HsvColor"(title, model) {
    return {
      component: "b-row",
      fieldOptions: {
        class: "isimple-form-row",
      },
      children: [
        {
          component: "b-input-group",
          fieldOptions: { class: "isimple-form-group" },
          children: [
            {
              component: "label",
              fieldOptions: {
                class: "mr-sm-2 isimple-form-label",
                style: { width: "90px" },
                domProps: { innerHTML: `${title} (h,s,v)` },
              },
            },
            {
              ...InputComponent.integer([model, "h"].join(".")),
            },
            {
              component: "div",
              fieldOptions: { class: "isimple-form-gap" },
            },
            {
              ...InputComponent.integer([model, "s"].join(".")),
            },
            {
              component: "div",
              fieldOptions: { class: "isimple-form-gap" },
            },
            {
              ...InputComponent.integer([model, "v"].join(".")),
            },
          ],
        },
      ],
    };
  },
  "#/definitions/FlipConfig"(title, model) {
    return {
      component: "b-row",
      fieldOptions: {
        class: "isimple-form-row",
      },
      children: [
        {
          component: "b-input-group",
          fieldOptions: { class: "isimple-form-group" },
          children: [
            {
              component: "label",
              fieldOptions: {
                class: "mr-sm-2 isimple-form-label",
                domProps: { innerHTML: `${title} horizontally` },
              },
            },
            {
              ...InputComponent.boolean(),
              model: [model, "horizontal"].join("."),
            },
            {
              component: "label",
              fieldOptions: {
                class: "mr-sm-2 isimple-form-label",
                domProps: { innerHTML: "vertically" },
              },
            },
            {
              ...InputComponent.boolean(),
              model: [model, "vertical"].join("."),
            },
          ],
        },
      ],
    };
  },
};

const Implementations = {
  "#/definitions/FeatureConfig"(title, model, schema, data, skip, order) {
    // console.log("FeatureConfig is here");
    // console.log(`title=${title}`);
    // console.log(`model=${model}`);
    // console.log("data=");
    // console.log(data);
  },
  "#/definitions/TransformConfig"(title, model, schema, data, skip, order) {
    // console.log("TransformConfig is here");
    // console.log(`title=${title}`);
    // console.log(`model=${model}`);
    // console.log("data=");
    // console.log(data);

    const type_model = [...model.split(".").slice(0, -1), "type"].join(".");
    // console.log(`type_model=${type_model}`);

    const type = get(data, type_model);
    // console.log(`type=${type}`);

    const data_schema = schema.implementations.TransformConfig[type];
    // console.log("data_schema=");
    // console.log(data_schema);

    const ui_schema = UiSchema(schema, data, skip, order, model, data_schema);
    // console.log("ui_schema=");
    // console.log(ui_schema);

    return ui_schema;
  },
  "#/definitions/FilterConfig"(title, model, schema, data, skip, order) {
    // console.log("FilterConfig is here");
    // console.log(`title=${title}`);
    // console.log(`model=${model}`);
    // console.log("data=");
    // console.log(data);

    const type_model = [...model.split(".").slice(0, -1), "type"].join(".");
    // console.log(`type_model=${type_model}`);

    const type = get(data, type_model);
    // console.log(`type=${type}`);

    const data_schema = schema.implementations.FilterConfig[type];
    // console.log("data_schema=");
    // console.log(data_schema);

    const ui_schema = UiSchema(schema, data, skip, order, model, data_schema);
    // console.log("ui_schema=");
    // console.log(ui_schema);

    return ui_schema;
  },
};

function getReference(property_schema) {
  if (property_schema.hasOwnProperty("$ref")) {
    return property_schema.$ref;
  } else if (property_schema.hasOwnProperty("allOf")) {
    return property_schema.allOf[0].$ref;
  } else {
    return undefined;
  }
}

function _handle_property(
  property,
  schema,
  data,
  skip,
  order,
  context,
  subschema,
  ui_schema
) {
  if (subschema.properties.hasOwnProperty(property)) {
    const model = context ? `${context}.${property}` : property;
    const value = get(data, model, undefined);

    // console.log(`model = ${model}`);

    if (skip.includes(model)) {
      // console.log(`skipping ${model}`);
    } else {
      // console.log(`property ${property}`);
      // console.log(subschema.properties[property]);

      // Check for reference & definition, recurse if found
      const reference = getReference(subschema.properties[property]);

      // console.log(reference);

      if (reference) {
        const definition = pointer.get(schema, reference.slice(1));

        if (Hardcoded.hasOwnProperty(reference)) {
          // todo: handle 'hardcoded' definitions here (for common definitions, e.g. Roi, Color, ...)

          // console.log(`HARDCODED DEFINITION -> ${reference}`);
          // console.log("properties=");
          // console.log(Object.keys(definition.properties));

          ui_schema = [...ui_schema, Hardcoded[reference](property, model)];
        } else if (Implementations.hasOwnProperty(reference)) {
          ui_schema = [
            ...ui_schema,
            getComponent.NESTED_CATEGORY(
              property,
              Implementations[reference](
                property,
                model,
                schema,
                data,
                skip,
                order
              )
            ),
          ];
        } else {
          const children = UiSchema(
            schema,
            data,
            skip + [[model, "name"].join(".")],
            order,
            context !== undefined ? [context, property].join(".") : property,
            definition
          );

          // console.log(property);
          // console.log("children=");
          // console.log(children);

          if (children.length > 0) {
            if (context) {
              ui_schema = [
                ...ui_schema,
                getComponent.NESTED_CATEGORY(property, children),
              ];
            } else {
              ui_schema = [
                ...ui_schema,
                getComponent.CATEGORY(property, children),
              ];
            }
          }
        }
      } else {
        const title =
          subschema.properties[property].description ||
          subschema.properties[property].title.toLowerCase();

        const type = subschema.properties[property].enum
          ? "enum"
          : subschema.properties[property].type;

        if (type === "array") {
          const item_reference = subschema.properties[property].items.$ref;

          // console.log("item_reference=");
          // console.log(item_reference);

          if (item_reference) {
            const item_definition = pointer.get(
              schema,
              item_reference.slice(1)
            );

            // console.log("item_definition=");
            // console.log(item_definition);

            if (value !== undefined) {
              var title_i;
              var skip_i;

              for (let i = 0; i < value.length; i++) {
                // console.log(item_definition.properties);

                if ("name" in item_definition.properties) {
                  title_i = `${title}[${i}] - ${get(
                    data,
                    `${model}[${i}].name`
                  )}`;
                  skip_i = skip + [`${model}[${i}].name`];
                } else {
                  title_i = title;
                  skip_i = skip;
                }

                const item_schema = UiSchema(
                  schema,
                  data,
                  skip_i,
                  order,
                  `${model}[${i}]`,
                  item_definition
                );

                if (item_schema.length > 0) {
                  if (context) {
                    ui_schema = [
                      ...ui_schema,
                      getComponent.NESTED_CATEGORY(title_i, item_schema), // todo: not writing model!
                    ];
                  } else {
                    ui_schema = [
                      ...ui_schema,
                      getComponent.CATEGORY(title_i, item_schema),
                    ];
                  }
                }
              }
            }
          } else {
            const item_type = subschema.properties[property].items;

            let items = [];

            if (value !== undefined) {
              for (let i = 0; i < value.length; i++) {
                const item_model = `${model}.${i}`; // todo: probably won't work
                items = [
                  ...items,
                  getComponent.FIELD("", item_type.type, item_model, {
                    enum_options: item_type.enum,
                    format: item_type.format, // todo: this is not used!
                  }),
                ];
              }
            }

            ui_schema = [
              ...ui_schema,
              getComponent.ARRAY(title, item_type, items),
            ];
          }
        } else if (type === "object") {
          // todo: handle arrays
          console.warn("THIS IS AN OBJECT I'M CONFUSED");
        } else {
          ui_schema = [
            ...ui_schema,
            getComponent.FIELD(title, type, model, {
              enum_options: subschema.properties[property].enum,
              format: subschema.properties[property].format,
            }),
          ];
        }
      }
    }
  }
  return ui_schema;
}

export function UiSchema(
  schema,
  data,
  skip = [],
  order = {},
  context = undefined,
  subschema = undefined
) {
  // console.log("ui-schema.UiSchema()");

  // console.log("schema=");
  // console.log(schema);

  // console.log("skip=");
  // console.log(skip);

  // console.log("context=");
  // console.log(context);

  try {
    assert(schema !== undefined);
    assert(schema.properties !== undefined);

    if (context !== undefined) {
      assert(subschema !== undefined);
      const subdata = data[context];
    } else {
      subschema = schema;
      const subdata = data;
    }

    let ui_schema = [];

    // console.log("We've got properties in this order: ");
    // console.log(subschema.properties);

    // console.log("Order for this context is: ");
    // console.log(order[context]);

    let properties = [];
    if (order[context]) {
      let unordered = Object.keys(subschema.properties);
      pullAll(unordered, order[context]);
      properties = [...order[context], ...unordered];
    } else {
      properties = Object.keys(subschema.properties);
    }

    for (let i = 0; i < properties.length; i++) {
      ui_schema = _handle_property(
        properties[i],
        schema,
        data,
        skip,
        order,
        context,
        subschema,
        ui_schema
      );
    }

    return ui_schema;
  } catch (err) {
    console.warn(`ui-schema.UiSchema() failed`);
    console.warn(err);
  }
}
