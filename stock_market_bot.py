import pandas as pd
from telegram import Bot
from telegram.ext import Updater, CommandHandler
from io import StringIO

from yahoo_fin import stock_info

bot = Bot(token='INSERT YOUR TOKEN')

def send_message(chat_id, message):
    bot.send_message(chat_id=chat_id, text=message)

# To get the current stock price
def get_stock_price(company_name):
    try:
        symbol = get_stock_symbol(company_name)
        price = stock_info.get_live_price(symbol)
        return price
    except Exception as e:
        return f"Error fetching stock data: {str(e)}"

# Converting a few companies to their symbol 
def get_stock_symbol(company_name):
    company_name = company_name.lower()
    if company_name == 'apple':
        return 'AAPL'
    elif company_name == 'google':
        return 'GOOGL'
    elif company_name == 'microsoft':
        return 'MSFT'
    # Add more mappings as needed
    else:
        return company_name.upper()  # Default to using the input as the symbol

# Initial message of the Bot
def start(update, context):
    update.message.reply_text('Welcome to the Stock Market Bot! Send /stock <company_name> to get detailed stock information.')

# Command handler for the /stock command
def stock(update, context):
    print("Received /stock command")

    company_name = ' '.join(context.args).capitalize()
    symbol = get_stock_symbol(company_name)

    try:
        current_price = get_stock_price(company_name)

        quote_table = stock_info.get_quote_table(symbol)

        previous_close_row = quote_table.append({'Attribute': 'Previous Close', 'Value': previous_close}, ignore_index=True)
        previous_close = float(previous_close_row['Value'].iloc[0])

        percentage_change = ((current_price - previous_close) / previous_close) * 100

        day_range = quote_table['Day\'s Range'].iloc[-1]  # Use iloc for position-based access
        day_low, day_high = map(float, day_range.split(' - '))

        message = f"Company: {company_name}\n"\
                  f"Current Price: ${current_price:.2f}\n"\
                  f"Previous Close: ${previous_close:.2f}\n"\
                  f"Percentage Change: {percentage_change:.2f}%\n"\
                  f"Day's Range: ${day_low} - ${day_high}"

        send_message(update.message.chat_id, message)

#For errors
    except Exception as e:

        error_message = f"Error fetching stock data for {company_name}: {str(e)}"
        send_message(update.message.chat_id, error_message)


def main():

    updater = Updater('INSERT YOUR TOKEN')

    dp = updater.dispatcher

    # Register the command handlers
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('stock', stock))

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
 