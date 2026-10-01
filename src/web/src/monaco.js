import * as monaco from "monaco-editor/editor/editor.api";
import "monaco-editor/languages/definitions/lua/register";
import editorWorker from "monaco-editor/editor/editor.worker?worker";

self.MonacoEnvironment = {
  getWorker() {
    return new editorWorker();
  },
};

function mix(hex, target, amount) {
  let h = String(hex).replace("#", "");
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  let n = parseInt(h, 16);
  if (Number.isNaN(n)) n = 0x8a8a8a;
  let r = (n >> 16) & 255;
  let g = (n >> 8) & 255;
  let b = n & 255;
  let blend = (from, to) => Math.round(from + (to - from) * amount);
  let out = (v) => v.toString(16).padStart(2, "0");
  return `#${out(blend(r, target[0]))}${out(blend(g, target[1]))}${out(blend(b, target[2]))}`;
}

function buildTheme(accent) {
  return {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "comment", foreground: "666666", fontStyle: "italic" },
      { token: "keyword", foreground: mix(accent, [255, 255, 255], 0.2), fontStyle: "bold" },
      { token: "keyword.local", foreground: mix(accent, [255, 255, 255], 0.05) },
      { token: "keyword.operator", foreground: mix(accent, [0, 0, 0], 0.3) },
      { token: "operator", foreground: "d4d4d4" },
      { token: "delimiter", foreground: "888888" },
      { token: "delimiter.bracket", foreground: "cccccc" },
      { token: "delimiter.parenthesis", foreground: "cccccc" },
      { token: "string", foreground: mix(accent, [0, 0, 0], 0.25) },
      { token: "string.escape", foreground: mix(accent, [255, 255, 255], 0.15) },
      { token: "number", foreground: mix(accent, [0, 0, 0], 0.18) },
      { token: "identifier", foreground: "dedede" },
      { token: "type", foreground: mix(accent, [255, 255, 255], 0.3) },
      { token: "function", foreground: mix(accent, [255, 255, 255], 0.26) },
      { token: "variable", foreground: "e6e6e6" },
    ],
    colors: {
      "editor.background": "#1a1a1a",
      "editor.foreground": "#d8d8d8",
      "editor.lineHighlightBackground": "#212121",
      "editorLineNumber.foreground": "#4d4d4d",
      "editorLineNumber.activeForeground": "#a0a0a0",
      "editorCursor.foreground": "#ffffff",
      "editor.selectionBackground": mix(accent, [0, 0, 0], 0.82),
      "editor.inactiveSelectionBackground": mix(accent, [0, 0, 0], 0.9),
      "editorIndentGuide.background1": "#242424",
      "editorIndentGuide.activeBackground1": "#383838",
      "scrollbarSlider.background": "#262626",
      "scrollbarSlider.hoverBackground": "#333333",
      "scrollbarSlider.activeBackground": "#404040",
      "editorBracketMatch.background": mix(accent, [0, 0, 0], 0.86),
      "editorBracketMatch.border": mix(accent, [255, 255, 255], 0.15),
      "editorBracketHighlight.foreground1": "#cccccc",
      "editorBracketHighlight.foreground2": "#cccccc",
      "editorBracketHighlight.foreground3": "#cccccc",
      "editorBracketHighlight.foreground4": "#cccccc",
      "editorBracketHighlight.foreground5": "#cccccc",
      "editorBracketHighlight.foreground6": "#cccccc",
      "editorBracketHighlight.unexpectedBracket.foreground": accent,
      "editorSuggestWidget.background": "#1b1b1b",
      "editorSuggestWidget.border": "#2a2a2a",
      "editorSuggestWidget.selectedBackground": "#2a2a2a",
      "editorHoverWidget.background": "#1b1b1b",
      "editorHoverWidget.border": "#2a2a2a",
    },
  };
}

monaco.editor.defineTheme("funnyexecutor-dark", buildTheme("#8a8a8a"));

export function applyAccent(accent) {
  monaco.editor.defineTheme("funnyexecutor-dark", buildTheme(accent));
  monaco.editor.setTheme("funnyexecutor-dark");
}

// --- luau language support ------------------------------------------------
// the shell ships the unc api tables (luau_api.py) so the web build and the
// native build stay in sync; register the providers once they arrive.

const LUA_LANGUAGE = "lua";
const providers = [];

function insideStringOrComment(model, pos) {
  const line = model.getValueInRange({
    startLineNumber: pos.lineNumber,
    startColumn: 1,
    endLineNumber: pos.lineNumber,
    endColumn: pos.column,
  });

  let quote = null;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (quote) {
      if (char === "\\") {
        i++;
        continue;
      }
      if (char === quote) quote = null;
    } else {
      if (char === '"' || char === "'") {
        quote = char;
      } else if (char === "-" && line[i + 1] === "-") {
        return true;
      }
    }
  }
  return quote !== null;
}

export function registerLuauProviders(api) {
  while (providers.length) {
    providers.pop().dispose();
  }
  if (!api || !Array.isArray(api.items)) return;

  const KIND = monaco.languages.CompletionItemKind;
  const SNIPPET = monaco.languages.CompletionItemInsertTextRule;

  providers.push(
    monaco.languages.registerCompletionItemProvider(LUA_LANGUAGE, {
      triggerCharacters: [".", ":"],
      provideCompletionItems(model, position) {
        if (insideStringOrComment(model, position)) {
          return { suggestions: [] };
        }
        const word = model.getWordUntilPosition(position);
        const range = {
          startLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endLineNumber: position.lineNumber,
          endColumn: word.endColumn,
        };

        return {
          suggestions: api.items.map((item) => ({
            label: item.label,
            kind: KIND[item.kind] || KIND.Text,
            detail: item.detail,
            insertText: item.insert || item.label,
            range,
            documentation: item.doc ? { value: item.doc } : undefined,
            insertTextRules: item.snippet ? SNIPPET.InsertAsSnippet : undefined,
          })),
        };
      },
    }),
  );

  providers.push(
    monaco.languages.registerHoverProvider(LUA_LANGUAGE, {
      provideHover(model, position) {
        if (insideStringOrComment(model, position)) return null;
        const word = model.getWordAtPosition(position);
        if (!word) return null;
        const info = api.hover?.[word.word];
        if (!info) return null;
        return {
          contents: [
            { value: "```lua\n" + info.sig + "\n```" },
            { value: info.doc },
          ],
        };
      },
    }),
  );

  providers.push(
    monaco.languages.registerSignatureHelpProvider(LUA_LANGUAGE, {
      signatureHelpTriggerCharacters: ["(", ","],
      signatureHelpRetriggerCharacters: [","],
      provideSignatureHelp(model, position) {
        if (insideStringOrComment(model, position)) return null;

        const line = model.getValueInRange({
          startLineNumber: position.lineNumber,
          startColumn: 1,
          endLineNumber: position.lineNumber,
          endColumn: position.column,
        });

        const match = line.match(/([A-Za-z_][\w.:]*)\s*\(([^()]*)$/);
        if (!match) return null;

        const name = match[1].split(".").pop().split(":").pop();
        const sig = api.signatures?.[name];
        if (!sig) return null;

        const active = match[2].split(",").length - 1;

        return {
          value: {
            signatures: [
              {
                label: sig.label,
                documentation: { value: sig.doc },
                parameters: sig.params.map((p) => ({ label: p })),
              },
            ],
            activeSignature: 0,
            activeParameter: Math.min(
              active,
              Math.max(sig.params.length - 1, 0),
            ),
          },
          dispose() {},
        };
      },
    }),
  );
}

export default monaco;