# Web frontend — Empório da Música

## Requirements

- Node.js 20.19 or later.
- The Empório da Música backend running at `http://localhost:8000`.

## Development

From the `frontend/` directory, install the dependencies and start Vite:

```bash
npm install
npm run dev
```

Open the local address printed in the terminal. Vite proxies `/api` and `/health` requests to the backend. Conversations are stored locally in the browser and shown in the sidebar, where they can be selected or deleted. The history is for display only; it is not sent to the agent as context or synchronized with the backend. Use the theme button in the top bar to switch between light and dark modes. The selected theme is saved in the browser.

## Validation

```bash
npm run lint
npm run build
```
