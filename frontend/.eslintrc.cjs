/* ESLint 配置（框架要求使用 CommonJS 入口，此处允许 module.exports） */
module.exports = {
  root: true,
  env: { browser: true, es2022: true, node: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "prettier",
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: "latest", sourceType: "module" },
  plugins: ["@typescript-eslint", "react-hooks", "react-refresh"],
  settings: { react: { version: "18.3" } },
  ignorePatterns: [
    "dist",
    "node_modules",
    "src/types/api.d.ts",
    "*.cjs",
    "postcss.config.js",
  ],
  rules: {
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "warn",
    // shadcn 约定：组件文件常并置 variants/hooks，关闭该 fast-refresh 提示
    "react-refresh/only-export-components": "off",
    "no-restricted-syntax": [
      "error",
      {
        selector: "ExportDefaultDeclaration",
        message: "禁止 export default，统一使用具名导出（框架入口除外）。",
      },
    ],
    "@typescript-eslint/no-unused-vars": [
      "error",
      { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
    ],
    "@typescript-eslint/no-explicit-any": "warn",
  },
  overrides: [
    {
      files: ["vite.config.ts", "tailwind.config.ts", "src/main.tsx"],
      rules: { "no-restricted-syntax": "off" },
    },
  ],
};
