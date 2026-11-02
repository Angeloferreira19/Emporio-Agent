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

Abra o endereço local exibido no terminal. O proxy do Vite encaminha `/api` e `/health` para o backend. As conversas ficam salvas localmente no navegador e aparecem na barra lateral, onde é possível alternar entre elas ou excluí-las. O histórico é apenas visual; ele não é enviado como contexto ao agente nem sincronizado com o backend. Use o botão de tema no topo para alternar entre os modos claro e escuro; a preferência fica salva no navegador.

## Validação

```bash
npm run lint
npm run build
```
