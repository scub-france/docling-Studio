import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import pluginVue from 'eslint-plugin-vue'

export default [
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    files: ['src/**/*.{ts,js,vue}'],
    languageOptions: {
      globals: {
        __APP_VERSION__: 'readonly',
      },
      parserOptions: {
        parser: tseslint.parser,
      },
    },
    rules: {
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'no-debugger': 'error',
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'off',
      // Decoupling invariant (#audit-07): cross-feature access only through the
      // public barrel (@/features/<name>) or @/shared — never into another
      // feature's internals (store/api/ui).
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: [
                '../*/store',
                '../*/store/*',
                '../*/api',
                '../*/api/*',
                '../*/ui/*',
                '../../*/store',
                '../../*/store/*',
                '../../*/api',
                '../../*/api/*',
                '../../*/ui/*',
                '@/features/*/store',
                '@/features/*/store/*',
                '@/features/*/api',
                '@/features/*/api/*',
                '@/features/*/ui/*',
              ],
              message:
                'Cross-feature imports must go through the public barrel (@/features/<name>) or @/shared. Deep imports into another feature are forbidden (#audit-07 / decoupling).',
            },
          ],
        },
      ],
      'vue/multi-word-component-names': 'off',
      'vue/require-default-prop': 'off',
      // Formatting handled by Prettier
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/html-closing-bracket-spacing': 'off',
      'vue/html-closing-bracket-newline': 'off',
      'vue/html-indent': 'off',
      'vue/html-self-closing': 'off',
      'vue/attributes-order': 'off',
    },
  },
  {
    // Test files may reach into feature internals to build mocks/fixtures.
    files: ['src/**/*.test.{ts,js}'],
    rules: {
      'no-restricted-imports': 'off',
    },
  },
  {
    ignores: ['dist/', 'node_modules/', '*.config.js'],
  },
]
