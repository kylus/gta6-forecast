# gta6-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/kylus/gta6-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/kylus/gta6-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

An hour-by-hour forecast of Grand Theft Auto VI's launch-day Twitch viewers, in Python 3 with the standard library only. Given hour 1's count, it turns every past launch the case carries into the ratios of that launch's hours 2 to 24 to its own hour 1, and writes each hour's five quantiles as hour 1's count times a weighted mixture of those ratios.

The weights say how much a past launch resembles this one: console games that unlock at midnight local time weigh most, global-simultaneous PC unlocks and free-to-play games least, early-access launches less, and launches whose hour-1 size or rise into the day is close to the target's more. The mixture is smoothed and blended with a random walk, so a thin analogue set cannot make it overconfident.

`tools/loo.py` scores it leave-one-launch-out on the comparables, with the contest's pinball loss on the log scale: on launches whose hour 1 is already a real share of the day's peak, 0.205 against 0.288 for persistence.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=mp1vhw1y&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
