# SriGEN Frontend

React + Vite project for the SriGEN sign-in / sign-up screen, set up so new
pages can be added without restructuring anything.

## Run it

```bash
npm i
npm run dev
```

Then open the URL Vite prints (usually http://localhost:5173).

```bash
npm run build      # production build into dist/
npm run preview    # preview the production build locally
```

## Structure

```
src/
  main.jsx          # React entry point
  App.jsx           # Router + route list — add new routes here
  index.css         # global reset
  pages/
    LoginPage.jsx    # sign-in / sign-up screen
    LoginPage.css
    Dashboard.jsx    # placeholder page shown after a successful sign-in
  assets/
    sriGen-background.jpg
```

## Adding a new page

1. Create `src/pages/YourPage.jsx` (and a matching `.css` file if it needs
   its own styles — each page keeps its own stylesheet, so pages don't
   fight each other's CSS).
2. Import it in `src/App.jsx`:
   ```jsx
   import YourPage from "./pages/YourPage.jsx";
   ```
3. Add a route in the same file:
   ```jsx
   <Route path="/your-path" element={<YourPage />} />
   ```

That's it — no other file needs to change.

## Connecting real auth

`src/pages/LoginPage.jsx` currently fakes sign-in/sign-up with a
`setTimeout`, clearly marked with a `// Demo behavior` comment in both
`handleSignInSubmit` and `handleSignUpSubmit`. Replace those blocks with
your real API calls. The component also accepts `onSignIn` and `onSignUp`
callback props if you'd rather keep API logic outside the component.
