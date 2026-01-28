# Driveway Tetris

A fun shared “where are the cars?” board.

## Zones
- Driveway Spot A
- Driveway Spot B
- Across the street
- Around the block
- Away

## How it works
- Drag car tokens between zones.
- Tap a token on mobile to cycle through zones.
- Unlimited guest cars (Add guest).

## Shared mode (Supabase)
This repo is hosted on GitHub Pages (static), so shared state needs a backend.

### Minimal schema
Create a table:

```sql
create table if not exists public.driveway_states (
  house_id text primary key,
  state jsonb not null,
  updated_at timestamptz not null default now()
);

-- Enable realtime on the table in Supabase UI.
```

### RLS (simple)
For v1, keep it frictionless but not wide-open to random internet writes.
Recommended: use a shared `house_id` that’s hard to guess, and allow reads/writes to any row.

Better v2: require a short “house passcode” or signed token.

### Configure
Edit `config.js`:

```js
window.DRIVEWAY_TETRIS = {
  SUPABASE_URL: "https://YOUR_PROJECT.supabase.co",
  SUPABASE_ANON_KEY: "YOUR_ANON_KEY",
};
```

## Notes
- Don’t put addresses or license plates.
- Use nicknames only.
