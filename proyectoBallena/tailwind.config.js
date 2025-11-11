/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './templates/**/*.django',
    './node_modules/flowbite/**/*.js'
  ],
  theme: {
    extend: {
      fontFamily: {
        'Inter': ['Inter', 'sans-serif'],
      },
      colors: {
        fondoPrimario: "",
        colorSecundario: "#111827",
        colorVerdeLogo: "#04AC34"
      },
      screens: {
        'xs': '455px',
      },
    },
  },
  plugins: [
    require('flowbite/plugin')
]
}

