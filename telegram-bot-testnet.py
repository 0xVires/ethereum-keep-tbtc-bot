import logging
import json
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from config_testnet_private import WS_LOCAL, TEL_TOKEN
from web3 import Web3

w3 = Web3(Web3.WebsocketProvider(WS_LOCAL))

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

SUBSCRIBE, REMOVE, AVAILABLE_COMMANDS = range(3)


def start(update, context):
    """Send a message when typing anything other than the available commands."""
    reply_keyboard = [['Subscribe', 'Remove'], 
                      ['My subscriptions', 'Available TDTs'],
                      ['Quit']]

    update.message.reply_text(
        "Welcome to the tBTC-Watcher bot! \n\n"
        "You can subscribe to an operator address to get notified about your staked ETH.",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard))
    return AVAILABLE_COMMANDS

def enter_address_subscribe(update, context):
    chat_id = update.message.chat.id #NOT NEEDED HERE
    user = update.message.from_user
    update.message.reply_text('Please enter your operator address.',
                              reply_markup=ReplyKeyboardRemove())
    return SUBSCRIBE

def enter_address_remove(update, context):
    user = update.message.from_user
    update.message.reply_text('Please enter your operator address.',
                              reply_markup=ReplyKeyboardRemove())
    return REMOVE

def subscribe(update, context):
    """Handles adding a subscription
    Cases: 
    1) operator & chat_id is already in subscriptions: do nothing
    2) o is in subscriptions but not c: append c to o
    3) o is not in subscriptions: add c & o
    """
    reply_keyboard = [['Subscribe', 'Remove'], 
                      ['My subscriptions', 'Available TDTs'],
                      ['Quit']]
    
    user = update.message.from_user
    chat_id = update.message.chat.id
    operatorAddr = update.message.text
    logger.info("Chat ID of %s: %s", user.first_name, chat_id)
    logger.info("Operator address: %s", operatorAddr)
    if w3.isAddress(operatorAddr):
        operatorChecksum = w3.toChecksumAddress(operatorAddr)
        with open("operator_subscriptions_testnet.json", "r") as f:
            subscriptions = json.load(f)
        if subscriptions.get(operatorChecksum):
            if chat_id in subscriptions[operatorChecksum]:
                update.message.reply_text("You are already subscribed to this address \n\n"
                                          "Anything else?", reply_markup=ReplyKeyboardMarkup(reply_keyboard))
                return AVAILABLE_COMMANDS
            else:
                subscriptions[operatorChecksum].append(chat_id)
        else:
            subscriptions[operatorChecksum] = [chat_id]
        with open("operator_subscriptions_testnet.json", "w") as f:
            json.dump(subscriptions, f, indent=1)
        update.message.reply_text("Subscription added, you will now get notified about events of {} \n\n"
                                  "Anything else?".format(operatorChecksum), reply_markup=ReplyKeyboardMarkup(reply_keyboard))
        return AVAILABLE_COMMANDS
    else:
        update.message.reply_text("This is not a valid address, please try again...")
        return SUBSCRIBE

def remove(update, context):
    """Handles subscription removal

    Check if the chat_id is subscribed to the operator.
    If true: delete chat_id from operator. 
    If the operator has no subscribers, remove the operator.
    """
    reply_keyboard = [['Subscribe', 'Remove'], 
                      ['My subscriptions', 'Available TDTs'],
                      ['Quit']]
    
    user = update.message.from_user
    chat_id = update.message.chat.id
    operatorAddr = update.message.text
    logger.info("Chat ID of %s: %s", user.first_name, chat_id)
    logger.info("Operator address: %s", operatorAddr)
    if w3.isAddress(operatorAddr):
        operatorChecksum = w3.toChecksumAddress(operatorAddr)
        with open("operator_subscriptions_testnet.json", "r") as f:
            subscriptions = json.load(f)
        if subscriptions.get(operatorChecksum):
            if chat_id in subscriptions[operatorChecksum]:
                subscriptions[operatorChecksum].remove(chat_id)
                if not subscriptions[operatorChecksum]:
                    del subscriptions[operatorChecksum]
                with open("operator_subscriptions_testnet.json", "w") as f:
                    json.dump(subscriptions, f, indent=1)
                update.message.reply_text("You are now unsubscribed from operator {} \n\n"
                                          "Anything else?".format(operatorChecksum), reply_markup=ReplyKeyboardMarkup(reply_keyboard))
                return AVAILABLE_COMMANDS
            else:
                update.message.reply_text("You are not subscribed to this operator \n\n"
                                          "Anything else?", reply_markup=ReplyKeyboardMarkup(reply_keyboard))
                return AVAILABLE_COMMANDS
        else:
            update.message.reply_text("You are not subscribed to this operator \n\n"
                                      "Anything else?", reply_markup=ReplyKeyboardMarkup(reply_keyboard))
            return AVAILABLE_COMMANDS
    else:
        update.message.reply_text("This is not a valid address, please try again...")
        return REMOVE

def available_tdts(update, context):
    reply_keyboard = [['Subscribe', 'Remove'], 
                      ['My subscriptions', 'Available TDTs'],
                      ['Quit']]
    chat_id = update.message.chat.id
    with open("operator_tdts_testnet.json", "r") as fh:
        otdts = json.load(fh)
    with open("operator_subscriptions_testnet.json", "r") as f:
        subscriptions = json.load(f)
    for o in subscriptions:
        if otdts.get(o):
            message = f"TDTs in vending machine for operator {o[:7]}:\n\n"       
            for tdt, eth in sorted(otdts[o].items(), key=lambda x: x[1], reverse=True):
                if tdt != "sumETH":
                    message += f"{tdt} : {eth} ETH\n"
            message += f"\nTotal ETH available to free up: {otdts[o]['sumETH']}"
            update.message.reply_text(message)
        else:
            update.message.reply_text("Since you subscribed, no ETH is available to free up.")
    update.message.reply_text("Anything else?", reply_markup=ReplyKeyboardMarkup(reply_keyboard))
    return AVAILABLE_COMMANDS

def subscriptions(update, context):
    reply_keyboard = [['Subscribe', 'Remove'], 
                      ['My subscriptions', 'Available TDTs'],
                      ['Quit']]
    chat_id = update.message.chat.id
    with open("operator_subscriptions_testnet.json", "r") as f:
        subscriptions = json.load(f)
    message = [t for t, cid in subscriptions.items() if chat_id in cid]
    update.message.reply_text("You are subscribed to the following operators:\n" + "\n".join(message))
    update.message.reply_text("Anything else?", reply_markup=ReplyKeyboardMarkup(reply_keyboard))
    return AVAILABLE_COMMANDS
    
def available_commands(update, context):
    """Send a message when typing anything other than the available commands."""
    reply_keyboard = [['Subscribe', 'Remove'], 
                      ['My subscriptions', 'Available TDTs'],
                      ['Quit']]

    update.message.reply_text(
        "The following options are available: \n"
        "Subscribe: Add a new subscription \n"
        "Remove: Unsubscribe from an address \n"
        "My subscriptions: Lists the addresses to which you are subscribed. \n"
        "Available TDTs: Lists the operator's TDTs that are currently in the vending machine and available to buy. \n"
        "Quit",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard))
    return AVAILABLE_COMMANDS


def quit(update, context):
    user = update.message.from_user
    logger.info("User %s canceled the setup.", user.first_name)
    update.message.reply_text('Conversation stopped - if you want to interact with the bot again, just type /hey',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END

def main():
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TEL_TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CommandHandler('hey', available_commands)],

        states={           
            AVAILABLE_COMMANDS: [MessageHandler(Filters.regex(r'Subscribe'), enter_address_subscribe),
                                 MessageHandler(Filters.regex(r'Remove'), enter_address_remove),
                                 MessageHandler(Filters.regex(r'My subscriptions'), subscriptions),
                                 MessageHandler(Filters.regex(r'Available TDTs'), available_tdts),
                                 MessageHandler(Filters.regex(r'Quit'), quit)],

            SUBSCRIBE: [MessageHandler(Filters.regex(r'0x'), subscribe)],
            
            REMOVE: [MessageHandler(Filters.regex(r'0x'), remove)]
        },

        fallbacks=[CommandHandler('quit', quit), MessageHandler(Filters.text, available_commands)]
    )

    dp.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()