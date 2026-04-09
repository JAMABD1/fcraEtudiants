/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        '../templates/**/*.html',
        '../../main/templates/main/**/*.html',
        '../../main/templates/main/components/**/*.html',
        '../../api/templates/api/**/*.html',
        '../../templates/**/*.html',
    ],
    darkMode: 'class',
    theme: {
        extend: {},
    },
    plugins: [
        require('@tailwindcss/forms'),
        require('@tailwindcss/typography'),
        require('@tailwindcss/aspect-ratio'),
    ],
}
