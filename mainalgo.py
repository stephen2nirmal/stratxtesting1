from binance.client import Client
import numpy as np
import pandas as pd
import asyncio
from aiogram import Bot
#----------------------------------------------------------------------------------------------Telegram
bot_token = '6773719862:AAG8L4dWOVGNbYW6OF3XIkeYxcdxrgObrFY'
chat_id = '1941701154' # Replace with the chat ID of the user or group you want to send the messages to

async def send_message(bot_token, chat_id, message):
    bot = Bot(token=bot_token)
    await bot.send_message(chat_id=chat_id, text=message)
    await bot.session.close()  # Close the client session explicitly


# Initialize the Binance client
api_key = 'XLOS3QSrcFtSSqkYZlSmVw2r5ySDkrDVNmfhOmtcx9f4lfcmuTOuYpPbB5rs3993'
api_secret = 'k8n9qVkNsteXCHjjZ5gBuCStRJmFXUj6uItlhI1hVqLWtwI0QtsC3Z0i4UTOPeiR'
client = Client(api_key, api_secret, testnet=True)


#---------------------------------------------------------------------------------------Defining Functions

def get_last_order_status(symbol):
    # Fetch recent trades
    recent_trades = client.get_my_trades(symbol=symbol, limit=1)
        # Check if there are any recent trades
    if len(recent_trades) > 0:
        last_trade = recent_trades[0]
        # Check if 'isBuyer' key exists in the trade data
        if 'isBuyer' in last_trade:
            asyncio.run(send_message(bot_token, chat_id, f"{last_trade}"))
            is_buyer = last_trade['isBuyer']
            if is_buyer:
                return 'BUY'
            else:
                return 'SELL'
        else:
            asyncio.run(send_message(bot_token, chat_id, "Error: 'isBuyer' key not found in trade data."))
            
            return None
    else:
        asyncio.run(send_message(bot_token, chat_id, "No recent trades found."))
        
        return None


def get_historical_data(symbol, interval, limit):
    try:
        klines = client.get_historical_klines(symbol=symbol, interval=interval, limit=limit)
        if not klines:
            raise ValueError("No data retrieved from Binance")
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
        df['close'] = df['close'].astype(float)
        return df
    except Exception as e:
        asyncio.run(send_message(bot_token, chat_id, f"Error fetching data: {e}"))
        
        return None
def ma_crossover_strategy(df, short_window=20, long_window=50):
    # Calculate short-term and long-term moving averages
    df['short_ma'] = df['close'].rolling(window=short_window).mean()
    df['long_ma'] = df['close'].rolling(window=long_window).mean()

    # Generate signals
    df['signal'] = 0
    df.loc[df['short_ma'] > df['long_ma'], 'signal'] = 1  # 1 indicates buy signal

    return df

def place_buy_order(symbol, quantity):
    try:
        order = client.create_order(
            symbol=symbol,
            side=Client.SIDE_BUY,
            type=Client.ORDER_TYPE_MARKET,
            quantity=quantity
        )
        asyncio.run(send_message(bot_token, chat_id, "Market buy order successfully placed."))
        
        return order
    except Exception as e:
        asyncio.run(send_message(bot_token, chat_id, f"Failed to place market buy order: {e}"))
        
        return None

def get_previous_order(symbol):
    try:
        # Fetch recent orders
        orders = client.get_my_trades(symbol=symbol, limit=1) #client.get_all_orders(symbol=symbol, limit=1)
        asyncio.run(send_message(bot_token, chat_id, f"Recent trades:{orders}"))
        
        
        if not orders:
            asyncio.run(send_message(bot_token, chat_id, "No previous orders found."))
            
            return None, None
        
        # Get the price and quantity of the previous order
        prev_order = orders[0]
        price = float(prev_order['price'])
        quantity = float(prev_order['qty'])
        
        return price, quantity
    except Exception as e:
        asyncio.run(send_message(bot_token, chat_id, f"Error fetching previous orders: {e}"))
        
        return None, None



def place_limit_order(symbol, price, quantity):
    try:
        order = client.create_order(
            symbol=symbol,
            side=Client.SIDE_SELL,
            type=Client.ORDER_TYPE_LIMIT,
            timeInForce=Client.TIME_IN_FORCE_GTC,  # Good 'Till Cancelled
            price=str(price),  # Convert price to string
            quantity=str(quantity)  # Convert quantity to string
        )
        asyncio.run(send_message(bot_token, chat_id, "Limit order successfully placed."))
        asyncio.run(send_message(bot_token, chat_id, "Waiting for order to be filled..."))
        
        # Wait until order is filled or canceled
        while True:
            order_status = client.get_order(symbol=symbol, orderId=order['orderId'])
            if order_status['status'] == 'FILLED':
                asyncio.run(send_message(bot_token, chat_id, "Limit order filled."))
                
                
                break
                
                
        
        return order
    except Exception as e:
        asyncio.run(send_message(bot_token, chat_id, f"Failed to place limit order: {e}"))
        
        return None


def calc_sellprice(price, profit):
    sell_price = round(price * (1 + profit))
    return sell_price

def execute():
    # Fetch historical data
    df = get_historical_data(symbol, interval, limit)
    # Apply MA crossover strategy
    df = ma_crossover_strategy(df)
    
    if last_order_status:
        asyncio.run(send_message(bot_token, chat_id, f"The last order placed for {symbol} was a {last_order_status} order."))
    else:
        asyncio.run(send_message(bot_token, chat_id, f"No recent orders found for {symbol}."))
    
    if last_order_status == 'SELL':
        asyncio.run(send_message(bot_token, chat_id, "BUY processing"))
        
        # Check if the latest signal is a buy signal
        latest_signal = df.iloc[-1]['signal']
        if latest_signal == 1:
            # Replace with the quantity of the asset you want to buy
            place_buy_order(symbol, quantity)
        else:
            asyncio.run(send_message(bot_token, chat_id, "No buy signal detected."))
    elif last_order_status == 'BUY':
        asyncio.run(send_message(bot_token, chat_id, "Sell processing"))
        
        # Place sell order with conditions
        prev_order_price, prev_order_quantity = get_previous_order(symbol)
        if prev_order_price is not None and prev_order_quantity is not None:
            price = calc_sellprice(prev_order_price, profit)
            asyncio.run(send_message(bot_token, chat_id, f"Previous order price: {prev_order_price}"))
            asyncio.run(send_message(bot_token, chat_id, f"Sell price with {profit*100}% profit: {price}"))
            asyncio.run(send_message(bot_token, chat_id, f"Previous order quantity: {prev_order_quantity}"))
            

            place_limit_order(symbol, price, prev_order_quantity)
    else:
        asyncio.run(send_message(bot_token, chat_id, f"No recent orders found for {symbol}."))
        


#------------------------------------------------------------------------- DATA For Running 




# Call the execute function
while True:
    symbol = 'BTCUSDT'  # Replace with your desired trading pair
    last_order_status = get_last_order_status(symbol)
    interval = Client.KLINE_INTERVAL_1HOUR  # 1-hour interval
    limit = 100  # Number of data points to retrieve
    quantity = 0.001
    profit = 0.003
    execute()

  


