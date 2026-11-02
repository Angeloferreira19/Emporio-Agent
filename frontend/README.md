# Interface web — Empório da Música

## Requisitos

- Node.js 20.19 ou superior.
- Backend da Empório da Música em execução em `http://localhost:8000`.

## Desenvolvimento

Na pasta `frontend/`, instale as dependências e inicie o Vite:

```bash
npm install
npm run dev
```

Abra o endereço local exibido no terminal. O proxy do Vite encaminha `/api` e `/health` para o backend.

## Validação

```bash
npm run lint
npm run build
```
