#!/usr/bin/env bash
# --------------------------------------------------------------------------- #
# Example usage of the Applifting SDK CLI                                     #
#                                                                             #
# Make the script executable (`chmod +x cli_usage.sh`) and run it, or copy    #
# individual commands to your terminal.                                       #
# --------------------------------------------------------------------------- #

# Either export your token once…
# export APPLIFTING_REFRESH_TOKEN="your-refresh-token"

# …or pass it explicitly with --refresh-token/-t.

###############################################################################
# Register a new product                                                      #
###############################################################################
applifting-sdk register-product \
  --name "CLI Widget" \
  --description "A widget registered from the CLI"

###############################################################################
# Fetch offers (replace <PRODUCT_ID> with the real UUID)                      #
###############################################################################
applifting-sdk get-offers <PRODUCT_ID>
