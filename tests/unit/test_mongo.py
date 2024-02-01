import unittest
import mongomock
from utils.mongodb_service import MongoDBService
from utils.constants import DEFAULT_MONGO_DB_NAME, DEFAULT_MONGO_SELL_ORDERS_COLLECTION, DEFAULT_MONGO_TRADES_COLLECTION
from tests.fixtures.multiple_trades import SOL_TRADES, ATOM_TRADES
from tests.fixtures.single_trade import ATOM_TRADE
from tests.fixtures.ticker_info import SOL_TICKER_PAIR, ATOM_TICKER_PAIR

class TestDatabaseQueriesWithMongomock(unittest.TestCase):
    def setUp(self):
        # Create a mongomock database
        self.mock_db = mongomock.MongoClient().db
        self.mongodb_service = MongoDBService("mongomock://localhost", DEFAULT_MONGO_DB_NAME, self.mock_db)

        docs_to_insert = SOL_TRADES + ATOM_TRADES
        for doc in docs_to_insert:
            self.mongodb_service.insert_one(DEFAULT_MONGO_TRADES_COLLECTION, doc)

    def tearDown(self):
        self.mongodb_service.delete_many(DEFAULT_MONGO_TRADES_COLLECTION)
        self.mongodb_service.delete_many(DEFAULT_MONGO_SELL_ORDERS_COLLECTION)
        
    def test_query_all_documents(self):
        all_docs = self.mongodb_service.query(DEFAULT_MONGO_TRADES_COLLECTION)

        expected_number = len(SOL_TRADES) + len(ATOM_TRADES)
        self.assertEqual(len(all_docs), expected_number)

    def test_query_specific_document(self):
        filter = {
            "id": "06256e71-3ee6-496a-aa26-61101f40a76e"
        }
        doc = self.mongodb_service.query(DEFAULT_MONGO_TRADES_COLLECTION, filter)
        self.assertEqual(len(doc), 1)   
    
    def test_delete_multiple_documents(self):
        all_sol_trades_ids = []
        for sol_doc in SOL_TRADES:
            all_sol_trades_ids.append(sol_doc["id"])
        
        delete_filter = {
            "id": {"$in": all_sol_trades_ids}
        }

        deletion_result = self.mongodb_service.delete_many(DEFAULT_MONGO_TRADES_COLLECTION, delete_filter)
        expected_deleted_count = 4
        self.assertEqual(deletion_result.deleted_count, expected_deleted_count)

        sol_filter = {
            "symbol": SOL_TICKER_PAIR
        }
        sol_docs = self.mongodb_service.query(DEFAULT_MONGO_TRADES_COLLECTION, sol_filter)
        expected_sol_docs = 0
        self.assertEqual(len(sol_docs), expected_sol_docs)

    def test_insert_single_document(self):
        single_atom_trade = ATOM_TRADE
        atom_filter = {
            "symbol": ATOM_TICKER_PAIR
        }

        atom_docs = self.mongodb_service.query(DEFAULT_MONGO_TRADES_COLLECTION, atom_filter)
        self.mongodb_service.insert_one(DEFAULT_MONGO_TRADES_COLLECTION, single_atom_trade)
        atom_docs_new = self.mongodb_service.query(DEFAULT_MONGO_TRADES_COLLECTION, atom_filter)

        self.assertEqual(len(atom_docs) + 1, len(atom_docs_new))

        
if __name__ == '__main__':
    unittest.main()