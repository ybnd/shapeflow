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

export function UiSchema(
  schema,
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
    } else {
      subschema = schema;
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
      const property = properties[i];

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
                ui_schema = [
                  ...ui_schema,
                  getComponent.CATEGORY(title, children),
                ];
              }
            }
          } else {
            const type = subschema.properties[property].enum
              ? "enum"
              : subschema.properties[property].type;

            if (type === "array") {
              // todo: handle arrays
              console.log("THIS IS AN ARRAY I'M CONFUSED");
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
