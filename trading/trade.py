from decimal import *

class Trade:

    def __init__(self, ticker: str, price: Decimal, shares: Decimal, fee: Decimal):
        self.ticker = ticker
        self.price = price
        self.shares = shares
        self.fee = fee
        self.total_cost = Decimal(0)
        self.num_trades = 0

    def updateCostBasis(self, price: Decimal, shares: Decimal, fee: Decimal):
        
        oldCost = self.price * self.shares
        additionalCost = price * shares

        self.price = (oldCost + additionalCost) / (self.shares + shares)
        self.shares = self.shares + shares
        self.fee = self.fee + fee
        self.num_trades = self.num_trades + 1