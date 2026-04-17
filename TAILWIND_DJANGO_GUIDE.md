# Tailwind CSS + Django Integration Guide

This guide outlines the integration of Tailwind CSS with Django in this project, using the `django-tailwind` package.

## 1. Project Structure
The project uses a dedicated Django app named `theme` to manage Tailwind CSS.
- `theme/`: The Django app for Tailwind.
- `theme/static_src/`: Contains the Tailwind source files, including `tailwind.config.js`.
- `theme/static/css/dist/styles.css`: The compiled CSS file used in production.

## 2. Configuration
The Tailwind configuration is located at `theme/static_src/tailwind.config.js`.

### Content Paths
Tailwind is configured to scan the following directories for classes:
- `theme/templates/**/*.html`
- `main/templates/main/**/*.html`
- `main/templates/main/components/**/*.html`
- `api/templates/api/**/*.html`
- `templates/**/*.html`

### Plugins
The following official Tailwind plugins are enabled:
- `@tailwindcss/forms`
- `@tailwindcss/typography`
- `@tailwindcss/aspect-ratio`

## 3. Usage in Templates
To use Tailwind in your Django templates:

1. Load the tags: `{% load tailwind_tags %}`
2. Include the CSS: `{% tailwind_css %}` in the `<head>` section.

Example (`base.html`):
```html
{% load static tailwind_tags %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    {% tailwind_css %}
</head>
<body>
    <h1 class="text-3xl font-bold underline">Hello world!</h1>
</body>
</html>
```

## 4. Development Workflow
To start the Tailwind development server (watcher):
```powershell
python manage.py tailwind start
```
This will automatically recompile your CSS whenever you change a template or the configuration.

## 5. Recommendations for Improvement

### A. Performance Optimization
- **Purge Unused CSS**: Ensure that all template paths are correctly listed in `tailwind.config.js` to avoid including unused styles in production.
- **Minification**: `django-tailwind` handles minification during the build process (`python manage.py tailwind build`). Always run this before deploying.

### B. Maintainability
- **Componentization**: Use Django's `{% include %}` or `{% block %}` to create reusable UI components. This keeps your templates clean and avoids repetition of Tailwind classes.
- **Custom Utilities**: If you find yourself repeating a long string of Tailwind classes, consider adding a custom utility or component in `theme/static_src/src/styles.css` using the `@apply` directive.

### C. Design System
- **Theme Customization**: Leverage the `theme` section in `tailwind.config.js` to define your project's color palette, typography, and spacing. This ensures consistency across the entire application.
- **Dark Mode**: The project is already configured for `darkMode: 'class'`. Implement a toggle to allow users to switch between light and dark themes.

### D. Tooling
- **Prettier**: Use Prettier with the `prettier-plugin-tailwindcss` to automatically sort your Tailwind classes. This makes the code much easier to read and maintain.
- **Browser Reload**: The project already has `django-browser-reload` installed. Ensure it is configured in `settings.py` and `urls.py` for a seamless development experience.
