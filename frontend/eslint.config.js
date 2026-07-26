import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

/**
 * O typecheck já cobre tipos; o lint existe para o que ele não vê — sobretudo as
 * regras dos hooks, onde um erro compila normalmente e quebra em tempo de
 * execução (dependência faltando num efeito, hook dentro de condicional).
 */
export default tseslint.config(
  { ignores: ["dist", "screenshots", "node_modules"] },
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // Parâmetro iniciado por `_` é descarte intencional.
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  },
  {
    // Scripts de automação rodam em Node, não no navegador.
    files: ["scripts/**/*.mjs", "*.config.{js,ts}"],
    languageOptions: { globals: globals.node },
  },
);
