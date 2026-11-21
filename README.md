# Official public calendar relay

Public economic-release and US equity-session calendar data only. No broker credentials, account data, trading state or order authority.

The workflow verifies and extracts the frozen public_calendar_relay.zip, runs its tests, retrieves only approved official sources, independently validates the output and publishes a Pages generation only on success. Archive SHA-256: 793e547b587e174c5e4bc2463ade59e272d65a921c1d0357e32eab0e29d5491e

Sources: BLS, Census, Federal Reserve, BEA, DOL and NYSE. Refresh: 04:17, 10:17, 16:17 and 22:17 UTC daily. Failed required-source validation retains the last successful deployment. Consumers must reject stale or unverified coverage.

Synthetic test fixtures are not real calendar coverage and are never published as a verified bundle.
