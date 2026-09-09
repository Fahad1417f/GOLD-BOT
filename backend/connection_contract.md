# GOLD-BOT live connection contract

The GitHub Pages UI is static. GitHub Pages does not execute the local Python/CDP agent, so the local V56 monitor publishes a read-only normalized state file to this repository. The browser reads that state directly from GitHub raw content.

- TradingView/CDP/Vision/KFOO remain local.
- Execution stays OFF.
- No GitHub token is stored in the repository.
- The local bridge requires a GitHub token with repository Contents: Read and write.
- State is published only when it changes and is throttled.
- Public state contains monitoring data only, never credentials or order commands.
