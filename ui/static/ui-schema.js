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
  FIELD(title, type, model, options) {
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

export function UiSchema(schema, context = "", subschema) {
  console.log("ui-schema.UiSchema()");
  assert(schema.properties !== undefined);

  if (context !== "") {
    assert(subschema !== undefined);
  } else {
    subschema = schema;
  }

  let ui_schema = [];

  for (const property in subschema.properties) {
    if (subschema.properties.hasOwnProperty(property)) {
      console.log(`property ${property}`);
      console.log(subschema.properties[property]);

      // Check for reference & definition, recurse if found
      const reference = getReference(subschema.properties[property]);

      const title =
        subschema.properties[property].description ||
        subschema.properties[property].title.toLowerCase();

      if (reference) {
        const definition = pointer.get(schema, reference.slice(1));
        const children = UiSchema(schema, property, definition);

        ui_schema = [...ui_schema, getComponent.CATEGORY(title, children)];
      } else {
        const type = subschema.properties[property].enum
          ? "enum"
          : subschema.properties[property].type;

        ui_schema = [
          ...ui_schema,
          getComponent.FIELD(title, type, `${context}.${property}`, {
            enum_options: subschema.properties[property].enum,
            format: subschema.properties[property].format,
          }),
        ];
      }
    }
  }

  return ui_schema;
}
