from decimal import Decimal

from .base_strategy import BaseStrategy
from utils.trading import calculate_profit_percent, TradeAction
from utils.logger import logger

class DynamicTrailingStop(BaseStrategy):
    """
    Dynamic take profit strategy with trailing stop functionality.
    
    Instead of fixed 10% exit, this:
    1. Activates trailing stop when profit reaches activation threshold
    2. Trails the highest price by a specified percentage
    3. Sells when price drops from highest by trail percentage
    
    This captures larger gains on strong momentum moves while protecting profits.
    
    Note: This is SOFTWARE-based trailing stop, not exchange order type.
    The bot tracks high water marks and triggers sells via normal limit orders.
    """
    
    def __init__(self, config, mongodb_service=None):
        parameters = config["parameters"]
        
        # Profit % to activate trailing stop (e.g., 8% = activate at 8% profit)
        self.activation_percent = Decimal(parameters.get("activation_percent", 8)) / 100
        
        # How much to trail from highest (e.g., 4% = sell if drops 4% from peak)
        self.trail_percent = Decimal(parameters.get("trail_percent", 4)) / 100
        
        # Absolute take profit if hit before trailing activates (safety net)
        self.absolute_take_profit = Decimal(parameters.get("absolute_take_profit", 15)) / 100
        
        super().__init__(config)
        
        self.mongodb_service = mongodb_service
        self.collection_name = "strategy_state"
        
        # Track highest prices for each position (stored in memory per bot run)
        # Key: position_id, Value: {"highest_bid": Decimal, "activated": bool}
        self.position_high_water_marks = {}
        
        # Load state from DB if available
        if self.mongodb_service:
            self._load_state()

    def _load_state(self):
        try:
            filter_dict = {"strategy": self.name}
            state_docs = self.mongodb_service.query(self.collection_name, filter_dict)
            for doc in state_docs:
                position_id = doc["position_id"]
                self.position_high_water_marks[position_id] = {
                    "highest_bid": Decimal(str(doc["highest_bid"])),
                    "activated": doc["activated"],
                    "entry_price": Decimal(str(doc["entry_price"]))
                }
            logger.info(f"{self.name}: Loaded state for {len(self.position_high_water_marks)} positions")
        except Exception as e:
            logger.error(f"{self.name}: Failed to load state: {e}")

    def _save_state(self, position_id):
        if not self.mongodb_service:
            return
            
        try:
            tracking = self.position_high_water_marks[position_id]
            document = {
                "strategy": self.name,
                "position_id": position_id,
                "highest_bid": float(tracking["highest_bid"]),
                "activated": tracking["activated"],
                "entry_price": float(tracking["entry_price"]),
                "updated_at": str(Decimal(0)) # Placeholder or timestamp
            }
            filter_dict = {"strategy": self.name, "position_id": position_id}
            self.mongodb_service.replace_one(self.collection_name, document, filter_dict, upsert=True)
        except Exception as e:
            logger.error(f"{self.name}: Failed to save state for {position_id}: {e}")

    def _delete_state(self, position_id):
        if not self.mongodb_service:
            return
            
        try:
            filter_dict = {"strategy": self.name, "position_id": position_id}
            self.mongodb_service.delete_many(self.collection_name, filter_dict)
        except Exception as e:
            logger.error(f"{self.name}: Failed to delete state for {position_id}: {e}")

    def eval(self, avg_position, candles_df, ticker_info):
        if not self.enabled:
            return TradeAction.NOOP
        
        # Only evaluate if we have positions
        if avg_position is None:
            return TradeAction.NOOP
        
        ticker = ticker_info["symbol"]
        current_bid = Decimal(str(ticker_info["bid"]))
        
        # Calculate current profit
        profit_pct = calculate_profit_percent(avg_position, ticker_info["bid"])
        
        # Safety net: absolute take profit (in case of extreme spike)
        if profit_pct >= self.absolute_take_profit:
            logger.info(f'{ticker}: {self.name} ABSOLUTE TAKE PROFIT triggered at {profit_pct*100:.2f}%')
            return TradeAction.SELL
        
        position_id = str(avg_position.get("id", "avg"))
        
        # Initialize tracking for this position if not exists
        if position_id not in self.position_high_water_marks:
            self.position_high_water_marks[position_id] = {
                "highest_bid": current_bid,
                "activated": False,
                "entry_price": Decimal(str(avg_position["price"]))
            }
        
        tracking = self.position_high_water_marks[position_id]
        
        # Update highest bid if current is higher
        if current_bid > tracking["highest_bid"]:
            tracking["highest_bid"] = current_bid
            logger.debug(f'{ticker}: {self.name} new high water mark: ${tracking["highest_bid"]:.4f}')
            self._save_state(position_id)
        
        # Activate trailing stop if profit threshold reached
        if profit_pct >= self.activation_percent and not tracking["activated"]:
            tracking["activated"] = True
            logger.info(f'{ticker}: {self.name} TRAILING STOP ACTIVATED at {profit_pct*100:.2f}% profit. '
                       f'Will trail by {self.trail_percent*100:.2f}%')
            self._save_state(position_id)
        
        # If trailing activated, check if we should sell
        if tracking["activated"]:
            # Calculate how far current price is from highest
            drop_from_highest = (tracking["highest_bid"] - current_bid) / tracking["highest_bid"]
            
            if drop_from_highest >= self.trail_percent:
                profit_locked_in = (current_bid - tracking["entry_price"]) / tracking["entry_price"]
                logger.info(f'{ticker}: {self.name} TRAILING STOP HIT - '
                           f'dropped {drop_from_highest*100:.2f}% from peak of ${tracking["highest_bid"]:.4f}. '
                           f'Locking in {profit_locked_in*100:.2f}% profit at ${current_bid:.4f}')
                
                # Clean up tracking (will be reinitialized if position reopened)
                del self.position_high_water_marks[position_id]
                self._delete_state(position_id)
                
                return TradeAction.SELL
            
            # Log current status
            logger.debug(f'{ticker}: {self.name} trailing - current: ${current_bid:.4f}, '
                        f'peak: ${tracking["highest_bid"]:.4f}, '
                        f'drop: {drop_from_highest*100:.2f}%, '
                        f'trail trigger: {self.trail_percent*100:.2f}%')

        return TradeAction.NOOP

    def cleanup_position(self, position_id):
        """
        Call this method when a position is closed externally
        to clean up tracking data.
        """
        if str(position_id) in self.position_high_water_marks:
            del self.position_high_water_marks[str(position_id)]
            self._delete_state(str(position_id))

