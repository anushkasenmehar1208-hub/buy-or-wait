# Buy or Wait? — Frontend

React 19 + TypeScript + Vite + Tailwind CSS client for the Buy or Wait? affordability assistant.

## Commands

```bash
npm install       # install dependencies
npm run dev       # dev server (http://localhost:5173)
npm run build     # type-check + production build to dist/
```

`src/App.tsx` (the real application root, in `src/app/`) mounts the router and providers.
The API base URL is configured with `VITE_API_BASE_URL` — see the repository root
`.env.example`.

## Structure

```
src/
├── app/                  # router, providers, protected layout
├── components/ui/        # design system (buttons, inputs, cards, dialogs, toasts)
├── features/
│   ├── auth/             # sign-in / sign-up pages, session context
│   ├── dashboard/        # overview: balance, safe-to-spend, recent decisions
│   ├── affordability/    # "Can I afford it?" flow + payment timeline chart
│   ├── financial-profile/# profile & income/expense/commitment/pending CRUD
│   └── history/          # decision history list + detail
├── services/             # typed API client (fetch + token handling)
├── types/                # shared TypeScript types mirroring the API contract
└── utils/                # formatting helpers
```

Sessions are JWT bearer tokens in `localStorage`; an expired/invalid token triggers a
redirect to sign-in with an explanatory notice. All financial decisions come from the
backend's deterministic engine — the frontend never calculates affordability itself.
