import assert from "assert";
import pointer from "json-pointer";

const InputComponent = {
  // todo: fill out with fitting Bootstrap components
  // todo: get inspired by BasicConfig layout
  enum({ enum_options }) {
    return {
      component: "b-form-select",
      fieldOptions: {
        on: "input",
        class: "isimple-form-field-input",
        attrs: { options: enum_options },
      },
    };
  },
  string() {
    return {
      component: "b-form-input",
      fieldOptions: {
        on: "input",
        class: ["isimple-form-field-input"],
      },
    };
  },
  integer() {
    return {
      component: "b-form-input",
      fieldOptions: {
        attrs: {
          type: "number",
        },
        on: { input: (value) => parseFloat(value) },
        class: "isimple-form-field-input",
      },
    };
  },
  float() {
    return {
      component: "b-form-input",
      fieldOptions: {
        attrs: {
          type: "number",
          step: 0.1,
        },
        on: { input: (value) => parseInt(value) },
        class: "isimple-form-field-input",
      },
    };
  },
  number() {
    // todo: not sure how or why this is in schema...
    return {
      component: "b-form-input",
      fieldOptions: {
        attrs: {
          type: "number",
          step: 0.1,
        },
        on: { input: (value) => parseInt(value) },
        class: "isimple-form-field-input",
      },
    };
  },
  boolean() {
    return {
      component: "b-form-select",
      fieldOptions: {
        on: "input",
        class: "isimple-form-field-checkbox",
        attrs: {
          options: [true, false],
        },
      },
    };
  },
};

const getComponent = {
  CATEGORY(title, children) {
    return {
      component: "b-card",
      fieldOptions: {
        class: "isimple-form-section",
        props: {
          header: title,
        },
      },
      children: children,
    };
  },
  NESTED_CATEGORY(title, children) {
    return {
      component: "b-card",
      fieldOptions: {
        class: "isimple-form-section-fit",
        props: {
          header: title,
        },
      },
      children: children,
    };
  },
  ARRAY(title, item_type, items) {
    console.log(`ARRAY() of type=${item_type}`);

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
    console.log(`FIELD() for type=${type}`);
    return {
      component: "b-row",
      fieldOptions: {
        class: "isimple-form-row",
      },
      children: [
        {
          component: "b-input-group",
          fieldOptions: {
            class: "isimple-form-group",
          },
          children: [
            {
              component: "b-input-group-text",
              fieldOptions: {
                class: "isimple-form-field-text",
                domProps: {
                  innerHTML: title,
                },
              },
            },
            {
              ...InputComponent[type](options),
              model: model,
            },
          ],
        },
      ],
    };
  },
};

function getReference(property_schema) {
  if (property_schema.hasOwnProperty("allOf")) {
    return property_schema.allOf[0].$ref;
  } else {
    return undefined;
  }
}

function getModelValue(data, model = "") {
  if (model) {
    let value = data;
    const attrs = model.split(".");
    for (let i = 0; i < attrs.length; i++) {
      value = value[attrs[i]]; // todo: this may be be a VueX no-no
    }
    return value;
  } else {
    return data;
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

    console.log(`model = ${model}`);

    if (skip.includes(model)) {
      console.log(`skipping ${model}`);
    } else {
      console.log(`property ${property}`);
      console.log(subschema.properties[property]);

      // Check for reference & definition, recurse if found
      const reference = getReference(subschema.properties[property]);

      const title =
        subschema.properties[property].description ||
        subschema.properties[property].title.toLowerCase();

      if (reference) {
        const definition = pointer.get(schema, reference.slice(1));
        const children = UiSchema(
          schema,
          data,
          skip,
          order,
          property,
          definition
        );

        if (children.length > 0) {
          if (context) {
            ui_schema = [
              ...ui_schema,
              getComponent.NESTED_CATEGORY(title, children),
            ];
          } else {
            ui_schema = [...ui_schema, getComponent.CATEGORY(title, children)];
          }
        }
      } else {
        const type = subschema.properties[property].enum
          ? "enum"
          : subschema.properties[property].type;

        if (type === "array") {
          const item_reference = subschema.properties[property].items.$ref;
          if (item_reference) {
            const item_definition = pointer.get(
              schema,
              item_reference.slice(1)
            );

            for (let i = 0; i < getModelValue(data, model).length; i++) {
              const item_schema = UiSchema(
                schema,
                data,
                skip,
                order,
                `${model}[${i}]`,
                item_definition
              );

              if (item_schema.length > 0) {
                if (context) {
                  ui_schema = [
                    ...ui_schema,
                    getComponent.NESTED_CATEGORY(title, item_schema), // todo: not writing model!
                  ];
                } else {
                  ui_schema = [
                    ...ui_schema,
                    getComponent.CATEGORY(title, item_schema),
                  ];
                }
              }
            }
          } else {
            const item_type = subschema.properties[property].items;

            let items = [];
            for (let i = 0; i < getModelValue(data, model).length; i++) {
              const item_model = `${model}.${i}`; // todo: probably won't work
              items = [
                ...items,
                getComponent.FIELD("", item_type[i].type, item_model, {
                  enum_options: item_type[i].enum,
                  format: item_type[i].format,
                }),
              ];
            }

            ui_schema = [
              ...ui_schema,
              getComponent.ARRAY(title, item_type, items),
            ];
          }
        } else if (type === "object") {
          // todo: handle arrays
          console.log("THIS IS AN OBJECT I'M CONFUSED");
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
  context = "",
  subschema
) {
  console.log("ui-schema.UiSchema()");

  console.log("schema=");
  console.log(schema);

  console.log("skip=");
  console.log(skip);

  try {
    assert(schema !== undefined);
    assert(schema.properties !== undefined);

    if (context !== "") {
      assert(subschema !== undefined);
      const subdata = data[context];
    } else {
      subschema = schema;
      const subdata = data;
    }

    let ui_schema = [];

    console.log("We've got properties in this order: ");
    console.log(subschema.properties);

    console.log("Order for this context is: ");
    console.log(order[context]);

    let properties = [];
    if (order[context]) {
      let unordered = Object.keys(subschema.properties);
      _.pullAll(unordered, order[context]);
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

    // todo: postprocess
    //  -> orphan fields on top
    //  -> fix order?

    return ui_schema;
  } catch (err) {
    console.warn(`ui-schema.UiSchema() failed`);
    console.warn(err);
  }
}
