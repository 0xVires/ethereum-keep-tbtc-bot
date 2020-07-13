import requests
import json
import time
from web3 import Web3
from config_mainnet_private import WS_LOCAL, MY_TELEGRAM_ID, TEL_TOKEN, TEL_URL
from config_mainnet_public import (ETH_NOTIFICATION_LIMIT, KeepBonding, TBTCDepositToken, Hex_VendingMachine, TBTCSystem, 
                    Topic0_KeepBonding_BondCreated, Topic0_TBTCDepositToken_Transfer, Topic0_TBTCSystem_RedemptionRequested,
                    Topic0_KeepBonding_BondReleased, BondedECDSAKeep_ABI)

w3 = Web3(Web3.WebsocketProvider(WS_LOCAL))

# 1) Deposit requested and created, ETH from Operators locked
def deposit_created(fromBlock, toBlock, subscriptions, ETH_NOTIFICATION_LIMIT):
    """Checks for created deposits between fromBlock and toBlock with a min amount of locked ETH.
    
    If an event exists, get the operator address and check if it is in the subscription list.
    If so, it sends a notification to the operator about the bonded/locked ETH amount and the tdtID.
    """

    bond_created_filter = w3.eth.filter({
    "fromBlock": fromBlock,
    "toBlock": toBlock,
    "address": KeepBonding,
    "topics": [Topic0_KeepBonding_BondCreated],
    })

    for event in bond_created_filter.get_all_entries():
        operator = w3.toChecksumAddress("0x" + event["topics"][1].hex()[26:])
        if subscriptions.get(operator):
            bondedETH = round(w3.toInt(hexstr=event["data"][2:][64:])/10**18, 5)
            if bondedETH > ETH_NOTIFICATION_LIMIT:
                BondedECDSAKeep = w3.toChecksumAddress("0x" + event["topics"][2].hex()[26:])
                ECDSA = w3.eth.contract(address=BondedECDSAKeep, abi=json.loads(BondedECDSAKeep_ABI))
                tdtID = str(w3.toInt(hexstr=ECDSA.functions.getOwner().call()))
                referenceID = w3.toInt(hexstr=event["data"][2:][:64])
                tx = event["transactionHash"].hex()
                # Create tdts json
                with open("tdts.json", "r") as f:
                    tdts = json.load(f)
                if tdts.get(tdtID):
                    # Avoid double entries in case script crashes
                    if str(operator) not in tdts[tdtID]["operators"]:
                        tdts[tdtID]["operators"].append(operator)
                else:
                    tdts[tdtID] = {}
                    tdts[tdtID]["operators"] = [operator]
                    tdts[tdtID]["bondedETH"] = bondedETH
                    tdts[tdtID]["referenceID"] = referenceID
                with open("tdts.json", "w") as f:
                    json.dump(tdts, f, indent=1)
                # Send notification
                message = f"Operator {operator[:7]}:\n{bondedETH} ETH was just bonded for the following TDT-ID: \n{tdtID} \n[Transaction link](https://etherscan.io/tx/{tx})"
                for chat_id in subscriptions[operator]:
                    send_message(message, chat_id)
                    time.sleep(1)

# 2) TDT to tBTC (sends TDT to vending machine)
def tdt_to_vendingMachine(fromBlock, toBlock, subscriptions):
    """Checks for TDTs sent to the vending machine between fromBlock and toBlock.
    
    If an event exists, get the TDT-ID and notify all subscribed operators backing that TDT.
    """
    #VendingMachine = "0xCa563c455B7DDa86D55310C71fBD6ed132c5C28C"
    
    tdt_to_vendingMachine_filter = w3.eth.filter({
    "fromBlock": fromBlock,
    "toBlock": toBlock,
    "address": TBTCDepositToken,
    "topics": [Topic0_TBTCDepositToken_Transfer, None, Hex_VendingMachine],
    })

    for event in tdt_to_vendingMachine_filter.get_all_entries():
        tdtID = str(w3.toInt(hexstr=event["topics"][3].hex()))
        with open("tdts.json", "r") as f:
            tdts = json.load(f)
        if tdtID in tdts:
            bondedETH = tdts[tdtID]["bondedETH"]
            tx = event["transactionHash"].hex()
            with open("tdts.json", "w") as f:
                json.dump(tdts, f, indent=1)
            for operator in tdts[tdtID]["operators"]:
                # Create operator-tdts json to display tdts available to buy
                write_operator_tdts(operator, tdtID, bondedETH)
                # Send notification
                message = f"Operator {operator[:7]}:\nTDT-ID \n{tdtID} \nis available to buy. You could release {bondedETH} ETH by buying it. \n[Transaction link](https://etherscan.io/tx/{tx})"
                for chat_id in subscriptions[operator]:
                    send_message(message, chat_id)
                    time.sleep(1)

# 3) tBTC to BTC Part 1: Redemption Requested (ETH still locked, but TDT transferred to requester -> notify that TDT can no longer be bought)
def redemption_requested(fromBlock, toBlock, subscriptions):
    """Checks for TDTs sent to the vending machine between fromBlock and toBlock.
    
    If an event exists, get the TDT-ID and notify all subscribed operators backing that TDT.
    """
   
    redemption_requested_filter = w3.eth.filter({
    "fromBlock": fromBlock,
    "toBlock": toBlock,
    "address": TBTCSystem,
    "topics": [Topic0_TBTCSystem_RedemptionRequested],
    })

    for event in redemption_requested_filter.get_all_entries():
        tdtID = str(w3.toInt(hexstr=event["topics"][1].hex()))
        with open("tdts.json", "r") as f:
            tdts = json.load(f)
        if tdtID in tdts:
            bondedETH = tdts[tdtID]["bondedETH"]
            tx = event["transactionHash"].hex()
            with open("tdts.json", "w") as f:
                json.dump(tdts, f, indent=1)
            for operator in tdts[tdtID]["operators"]:              
                # Remove TDT from "available to buy" status
                with open("operator_tdts.json", "r") as f:
                    otdts = json.load(f)
                otdts[operator]["sumETH"] -= otdts[operator][tdtID]
                del otdts[operator][tdtID]
                with open("operator_tdts.json", "w") as f:
                    json.dump(otdts, f, indent=1)  
                # Send notification  
                message = f"Operator {operator[:7]}:\nRedemption requested for TDT-ID {tdtID} \nYour bonded ETH ({bondedETH}) will be released soon! \n[Transaction link](https://etherscan.io/tx/{tx})"
                for chat_id in subscriptions[operator]:
                    send_message(message, chat_id)
                    time.sleep(1)

# 4) tBTC to BTC Part 2: Bond released & redeemed OR BTC Deposit/Setup failed and bond released...
def bond_released(fromBlock, toBlock, subscriptions):
    """Checks for released bonds between fromBlock and toBlock.
    
    If an event exists, get the reference-ID, match it with the TDT-ID and notify all subscribed operators backing that TDT.
    At the end, remove the TDT from the json (since the bond is released).
    """
    
    bond_released_filter = w3.eth.filter({
    "fromBlock": fromBlock,
    "toBlock": toBlock,
    "address": KeepBonding,
    "topics": [Topic0_KeepBonding_BondReleased],
    })

    for event in bond_released_filter.get_all_entries():
        operator = w3.toChecksumAddress("0x" + event["topics"][1].hex()[26:])
        if subscriptions.get(operator):
            referenceID = w3.toInt(hexstr=event["topics"][2].hex())  
            print(referenceID)
            tx = event["transactionHash"].hex()
            with open("tdts.json", "r") as f:
                tdts = json.load(f)
            # look for reference ID in tdts
            for tdtID in list(tdts):
                if tdts[tdtID]["referenceID"] == referenceID:         
                    bondedETH = tdts[tdtID]["bondedETH"]
                    tx = event["transactionHash"].hex()
                    message = f"Operator {operator[:7]}:\n{bondedETH} ETH bonded to TDT-ID {tdtID} was just released! \n[Transaction link](https://etherscan.io/tx/{tx})"
                    for chat_id in subscriptions[operator]:
                        send_message(message, chat_id)
                        time.sleep(1)
                    del tdts[tdtID]
                    with open("tdts.json", "w") as f:
                        json.dump(tdts, f, indent=1)

# Write operator-tdts json to list all the TDTs available to buy from an operator
def write_operator_tdts(operator, tdtID, bondedETH):
    with open("operator_tdts.json", "r") as f:
        otdts = json.load(f)                
    if not otdts.get(operator):
        otdts[operator] = {}
        otdts[operator]["sumETH"] = bondedETH
        otdts[operator][tdtID] = bondedETH
    else:   
        otdts[operator]["sumETH"] += bondedETH
        otdts[operator][tdtID] = bondedETH
    with open("operator_tdts.json", "w") as f:
        json.dump(otdts, f, indent=1)  

# Telegram - send message
def send_message(text, chat_id):
    sendURL = TEL_URL + "sendMessage?text={}&chat_id={}&parse_mode=markdown&disable_web_page_preview=True".format(text, chat_id)
    try:
        requests.get(sendURL)
    except Exception as ex:
        print(ex)

def main():
    # Read previous blocknumber and get new blocknumber (-5)
    # If there is no entry in the txt file, get current blocknumber - 50 (~10min ago)
    with open('block_record.txt', 'r') as fh:
    blockOld = fh.readlines()
    if not blockOld:
        blockOld = w3.eth.blockNumber - 50
    else:
        blockOld = int(blockOld[0])
    block = w3.eth.blockNumber - 5
    # Load subscribers
    with open("operator_subscriptions.json", "r") as f:
        subscriptions = json.load(f)
    # Check for events
    try:
        deposit_created(blockOld, block, subscriptions, ETH_NOTIFICATION_LIMIT)
        tdt_to_vendingMachine(blockOld, block, subscriptions)
        redemption_requested(blockOld, block, subscriptions)
        bond_released(blockOld, block, subscriptions)
        # Write new processed blocknumber to file
        with open('block_record.txt', 'w') as fh:
            fh.write(str(block))
    except Exception as ex:
        print(ex)
        send_message(ex, MY_TELEGRAM_ID)

if __name__ == '__main__':
    main()