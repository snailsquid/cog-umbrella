# umbrella

Tells you whether to take an umbrella today, using the free [Open-Meteo](https://open-meteo.com) API (no key).

## Commands

| Command | Who | What |
|---|---|---|
| `[p]umbrella [place]` | anyone | Today's rain chance, expected mm, high temperature and wettest hours for `place` (or your home city). |
| `[p]umbrella home [place]` | anyone | Save your default city; no argument clears it. |

"Take an umbrella" when today's max rain chance is ≥ 40%.

## Events emitted

| Event | Listener signature | When |
|---|---|---|
| `umbrella_forecast` | `on_umbrella_forecast(self, user: discord.abc.User, place: str, chance: int)` | After a forecast is shown. |

## Public methods

None.

## Data

Per-user `home` city (Red `Config`), cleared by `red_delete_data_for_user`.

## Secrets

None.
