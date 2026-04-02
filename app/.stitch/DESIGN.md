# ShooterDigest Design Tokens

Source: Stitch design-reference.html
Theme: Dark tactical intelligence dashboard
Applied: 2026-04-02

## Fonts

| Role | Family |
|------|--------|
| Sans (headline, body, label) | Inter |
| Mono (data, numbers) | JetBrains Mono |

## Color Tokens

### Backgrounds

| Token | Hex | Usage |
|-------|-----|-------|
| `--color-bg` | #131313 | Page background |
| `--color-surface` | #201f1f | Card / container background |
| `--color-surface-high` | #2a2a2a | Elevated surface (hover states, modals) |
| `--color-surface-bright` | #3a3939 | Highest elevation surface |

### Text

| Token | Hex | Usage |
|-------|-----|-------|
| `--color-text` | #e5e2e1 | Primary text |
| `--color-text-muted` | #c2c6d6 | Secondary text, descriptions |
| `--color-text-subtle` | #8c909f | Tertiary text, labels, timestamps |

### Accent Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `--color-accent` | #adc6ff | Primary accent (cool blue), links |
| `--color-accent-hover` | #4d8eff | Accent hover / active state |
| `--color-secondary` | #4ae176 | Positive signals, growth, green |
| `--color-secondary-hover` | #00b954 | Secondary hover / active state |
| `--color-tertiary` | #ffb3ad | Negative signals, decline, red/coral |
| `--color-error` | #ffb4ab | Error states |

### Borders

| Token | Value | Usage |
|-------|-------|-------|
| `--color-border` | rgba(255,255,255,0.08) | Default borders |
| `--color-border-hover` | rgba(255,255,255,0.14) | Hover / active borders |

## Extended Palette (from Stitch source)

These are the full Material-style tokens from the Stitch export. The tokens above are the working subset used in Tailwind.

| Stitch Token | Hex |
|---|---|
| background | #131313 |
| surface | #131313 |
| surface-container | #201f1f |
| surface-container-high | #2a2a2a |
| surface-container-highest | #353534 |
| surface-container-low | #1c1b1b |
| surface-container-lowest | #0e0e0e |
| surface-bright | #3a3939 |
| on-surface | #e5e2e1 |
| on-surface-variant | #c2c6d6 |
| primary | #adc6ff |
| primary-container | #4d8eff |
| on-primary | #002e6a |
| secondary | #4ae176 |
| secondary-container | #00b954 |
| on-secondary | #003915 |
| tertiary | #ffb3ad |
| tertiary-container | #ff5451 |
| error | #ffb4ab |
| error-container | #93000a |
| outline | #8c909f |
| outline-variant | #424754 |

## Shape

| Property | Value |
|----------|-------|
| border-radius | 0rem (sharp corners) |

## Tailwind Usage

All tokens are available as Tailwind v4 utilities via `@theme inline`:

```
bg-bg              -> #131313
bg-surface          -> #201f1f
bg-surface-high     -> #2a2a2a
bg-surface-bright   -> #3a3939
text-text           -> #e5e2e1
text-text-muted     -> #c2c6d6
text-text-subtle    -> #8c909f
text-accent         -> #adc6ff
text-secondary      -> #4ae176
text-tertiary       -> #ffb3ad
border-border       -> rgba(255,255,255,0.08)
border-border-hover -> rgba(255,255,255,0.14)
font-sans           -> Inter
font-mono           -> JetBrains Mono
```
