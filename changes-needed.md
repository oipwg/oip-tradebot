# Changes to TradeBot
TradeBot is currently designed to receive API requests to do two things:
1. `/tradebot/flobalance` ([link](https://api.alexandria.io/tradebot/flobalance)) - returns qty of Flo available to be traded
1. `/tradebot/depositaddress?floaddress=$FLOADDRESS` ([example1](https://api.alexandria.io/tradebot/depositaddress?floaddress=FEJVkMPgtcJLitwo5gGAyVNbEYNSZy9nyo) & [example2](https://api.alexandria.io/tradebot/depositaddress?floaddress=FEJVkMPgtcJLitwo5gGAyVNbEYNSZy9nyo&raw=True)) - returns a BTC address to send to, when it receives it will send the appropriate qty of Flo tokens to the supplied $FLOADDRESS

* As designed, it assumes that all trades will be between FLO and BTC.  
* Also, it only allows trades with one FLO holder.  
* Finally, it only allows trades to happen at the current spot market price.

As such, the following changes will need to be implemented:
1. The `/tradebot/depositaddress` endpoint will need to be able to accept a variable for which token will be traded for Flo, like such:  
  `/tradebot/depositaddress?=FEJVkMPgtcJLitwo5gGAyVNbEYNSZy9nyo&pairing=BTC` or  
  `/tradebot/depositaddress?=FEJVkMPgtcJLitwo5gGAyVNbEYNSZy9nyo&pairing=LTC`
1. A new component called "Autominer Traffic Manager" will need to be developed to allow more than one FLO holder to serve as the counter-party in trades. This component will be run at the application layer, by retailers or whoever else wishes to provide a pool of Flo available to those who need some. It is described in detail below.
1. TradeBot will need to be updated to use the "Historian Data Points" in order to respect specific "Offer Prices" of Autominers based on their actual cost to mine.

# Changes to Historian
* Add field: `http endpoint URL` to registration message
* Add value to historian data points: `litecoin:price_usd` from [this endpoint](https://api.coinmarketcap.com/v1/ticker/litecoin/)

# New Component: Autominer Traffic Manager
## What is it?
TradeBot's ultimate goal is to be a connector between the users who run Autominer applications to mine Flo on-goingly, and the users who are in need of Flo intermittently.

Ultimately, we want it to be a fully decentralized swap process, that will require two important decentralized technologies:  

1. Peer to Peer Messaging
1. Cross-chain atomic swaps

For the first, we're still considering options, as there are a few appealing ones currently. For the latter, first we need to upgrade Florincoin to include SegWit, which we're working on. Second, LN needs a decent amount more time in testing and working in a production environment. In the meanwhile, there is a relatively simple solution to stand in for both requirements for now: ***using hosted API endpoints.*** This limits how many users can serve on the "offer" side of trades for now, but will allow a few companies and dedicated users to provide the service for the time being.

## Persistent Process
Scan all Florincoin transactions as they get confirmed, looking for "open offers" in the coinbase transaction message, (Labeled as "oip-historian-2") and index this data as it comes in.  

## Trade Requests
* When a new “trade request” comes in, get two pieces of info from the user, their needed “publish fee” **(in USD)**, and which token they wish to pay for their trade with, BTC or LTC   
* Look through “open offers” in blockchain, starting at oldest (this is a table in the main db)
* make `publish fee needed` = `publish fee`
* loop:  
  1. at next open offer, get `offer price`, `flo offered` & `flo address` (this will need an additional API endpoint)  
  1. `flo needed` = `publish fee needed` / `offer price`
  1. if `flo offered` ≥ `flo needed`, end loop  
  1. if `flo offered` < `flo needed`, store the details of the offer (`offer price`, `flo offered` & `flo address`), do this: `publish fee` = `publish fee needed` - (`flo offered` x `offer price`)  and then go back to step 1 
* Sometimes this loop will end after finding just one offer, which is nice and simple, but in many cases it'll involve a few offers.
* For each stored offer, get the `flo address` and look it up in the list of registered Autominers (https://api.alexandria.io/alexandria/v2/autominer/get/all)
* Get from the corresponding Autominer registration the value for `endpoint url` (this is being added)
* Confirm the API is active and get the BTC or LTC send-to address by sending a GET to `https://api.alexandria.io/tradebot/depositaddress?floaddress=$PUBLISHERSFLOADDRESS&pairing=$TOKEN`
* If it responds with an address, its up, proceed by accepting the offer by sending the appropriate amount of BTC or LTC to it
* Once expected Flo is received, close the "open offer" by changing its status in the db file
