####Step 1: Offer a miner for rental
A user with a Scrypt ASIC miner (hereafter <b>hash rentee</b>) uses Librarian to list their miner for rent by publishing a message with their:   
<b>Price per MH/s per Hour</b>, the <b>Min Rental Hours</b> & <b>Max Rental Hours</b> and their hardware's estimated average <b>Hashrate</b>   

####Step 2: Rent the miner   
A user with BTC (or USD) to spend and wishes to rent a Scrypt ASIC miner (hereafter <b>hash renter</b>) uses Librarian to search for available miners. <b>Hash renter</b> selects some rigs and rents them. Payment for the rental is sent using BTC and pool instructions (*pool address, worker* & *password*) are sent via a P2P message to the chosen <b>hash rentee</b>.   

####Step 3: Send hashes to pool.alexandria.media   
Following the <b>hash renter</b>'s instructions, the <b>hash rentee</b> configures their miner to send hashes to the Alexandria pool.   

####Step 4: Receive block-rewards   
The *worker* that the <b>hash renter</b> provides is the *florincoin* address that they will receive block-reward payouts to.  These payouts include the following data in the `tx-comment` field:   
`Total Florincoin Hashrate`   
`Total Alexandria Pool Hashrate`   
List of all of the `Price per MH/s per Hour` of all currently rented Scrypt miners   
`Total Block Reward` in current block (including TX-fees)
`Blocks Won by Pool in 24h`

####Step 5: Scrape, Calculate & Index Open Trade Offers   
Use the following calculation to compute the <b>Pool Cost Basis per Block</b> for each block that the Alexandria pool wins:   
Average(`Price per MH/s per Hour` of all currently rented Scrypt miners) x `Total Alexandria Pool Hashrate` ÷ (60 ÷ 40 x 60)   
*Example*: `$0.005659 per MH/s per Hour` x `38 MH/s` ÷ (60 ÷ 40 x 60) =  `$0.00537 per Block`   

Use the following calculation to computer the <b>Pool Cost Basis Per Token</b> for each block that the Alexandria pool wins:   
<b>Pool Cost Basis per Block</b> ÷ <b>Total Block Reward</b>   
*Example*: `$0.00537 per Block` ÷ `50` = `$0.0001074 per Token`

####Step 6: Publish an Artifact   
A user who wishes to sell an album with Alexandria (hereafter <b>publisher</b>) uses Librarian to select the files for their album and fills out the fields needed. They chose a total purchase price for their album of $8. In order to publish, they must include a tx-fee of an equivalent number of Florincoins to their album's purchase price, $8. If they have enough Florincoin in their wallet, they can use them to publish. If they do not, TradeBot will be used in the background to exchange $5 worth of Florincoins, valued at 
