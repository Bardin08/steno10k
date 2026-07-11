/**
 * steno10k local ESLint rules — design-law enforcement.
 * Flat-config plugin: { rules: { "no-raw-hex", "no-emoji" } }.
 */

// 3/4/6/8-digit hex color, e.g. #fff #3f6b52 #3f6b52ff — but NOT "#/route" or "#top".
const HEX = /#[0-9a-fA-F]{3,4}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{8}\b/;
const EMOJI = /\p{Extended_Pictographic}/u;

function checkText(context, node, raw, key) {
  const re = key === "rawHex" ? HEX : EMOJI;
  if (typeof raw === "string" && re.test(raw)) {
    context.report({ node, messageId: key });
  }
}

const noRawHex = {
  meta: {
    type: "problem",
    docs: { description: "Ban hardcoded hex colors; use design tokens." },
    messages: {
      rawHex:
        "Raw hex color is banned — reference a design token (var(--color-*) / a token utility).",
    },
    schema: [],
  },
  create(context) {
    return {
      Literal(node) {
        checkText(context, node, node.value, "rawHex");
      },
      TemplateElement(node) {
        checkText(context, node, node.value.raw, "rawHex");
      },
      JSXText(node) {
        checkText(context, node, node.value, "rawHex");
      },
    };
  },
};

const noEmoji = {
  meta: {
    type: "problem",
    docs: { description: "Ban emoji in UI code; use Phosphor SVG icons." },
    messages: { emoji: "Emoji is banned — use a Phosphor SVG icon instead." },
    schema: [],
  },
  create(context) {
    return {
      Literal(node) {
        checkText(context, node, node.value, "emoji");
      },
      TemplateElement(node) {
        checkText(context, node, node.value.raw, "emoji");
      },
      JSXText(node) {
        checkText(context, node, node.value, "emoji");
      },
    };
  },
};

export default { rules: { "no-raw-hex": noRawHex, "no-emoji": noEmoji } };
