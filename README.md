# ethereum-keep-tbtc-bot
Sends telegram notifications about activities of the Keep/tBTC contracts on the Ethereum blockchain.

## libraries

Apart from the standard python libraries, the bot uses Web3.py (https://web3py.readthedocs.io/) and python-telegram-bot (https://github.com/python-telegram-bot/python-telegram-bot). 

## telegram-bot.py
Takes care of subscriptions to operator addresses. 
Stores those addresses with the chat_ids in operator_subscriptions.json

## tbtc-watcher.py
Keeps you informed about the state of your staked ETH.

The following events are being tracked:
1. A deposit is requested and created -> ETH from operators is locked
2. The TDT of the deposit is sent to the vending machine in exchange for tBTC -> Operator could buy the TDT to free up ETH
3. tBTC to BTC Part 1: A redemption is requested -> Operator's ETH is still locked, but the TDT is transferred to the requester and can no longer be bought
4. tBTC to BTC Part 2: The bonded ETH is released. (Note: This could also be the case if the BTC Deposit/Setup failed/timed out, in this case step 2 & 3 would be skipped)

The bot is currently set to only send notifications for ETH bonds with a value larger than 1 ETH. This can be adjusted via the config.py file.

The idea is to run tbtc-watcher.py every ~10min or so. The watcher will then process all the blocks that occured during those 10min and send notifications accordingly.
In my experience, this is a more robust setup than subscribing to new events where e.g. small issues with the node or uncle-blocks could cause blocks to be missed.

Please note that this bot is still in alpha. I'll test it more and make the necessary contract/function adjustments once tBTC relaunches.

**I'm planning on adding more features like liquidation warnings etc. If you have suggestions, please raise an Issue here on github or contact me on Discord (vires-in-numeris in the Keep-Channel)**
