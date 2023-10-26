from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, PyMongoError
import urllib.parse

class MongoDBService:
    _client = None

    @classmethod
    def _get_client(cls, db_url):
        if cls._client is None:
            try:
                cls._client = MongoClient(db_url)
                # You might want to add more robust connection handling and setup here
            except ConnectionFailure as e:
                print(f"Could not connect to server: {e}")
        return cls._client
    
    def __init__(self, db_url, db_name):
        """
        Initialize the MongoDBService with the specified database URL and database name.

        :param db_url: URL for the MongoDB database.
        :param db_name: Name of the database to interact with.
        """
        self.db_client = self._get_client(db_url)
        self.db = self.db_client[db_name]

    def query(self, collection, filter_dict=None, projection=None):
        """
        Query the specified collection with the given filter and projection.

        :param collection: Name of the collection to query.
        :param filter_dict: Dictionary specifying the query criteria.
        :param projection: Dictionary specifying which fields to include or exclude.
        :return: Query result as a list of dictionaries.
        """
        if filter_dict is None:
            filter_dict = {}

        try:
            if self.db is None:
                raise OperationFailure("Database not accessible")

            # Access the specified collection in the database and perform the query
            coll = self.db[collection]
            results = list(coll.find(filter_dict, projection))
            return results

        except OperationFailure as e:
            # Handle failed operation details
            print(f"Operation failed: {e}")
        except PyMongoError as e:
            # Handle any other PyMongo errors
            print(f"An error occurred while querying: {e}")

    def insert_one(self, collection, document):
        try:
            if self.db is None:
                raise OperationFailure("Database not accessible")
            
            coll = self.db[collection]
            coll.insert_one(document)

        except OperationFailure as e:
            # Handle failed operation details
            print(f"Operation failed: {e}")
        except PyMongoError as e:
            # Handle any other PyMongo errors
            print(f"An error occurred while querying: {e}")


    def delete_many(self, collection, filter_dict=None):
        if filter_dict is None:
            filter_dict = {}

        try:
            if self.db is None:
                raise OperationFailure("Database not accessible")
            
            coll = self.db[collection]
            coll.delete_many(filter_dict)

        except OperationFailure as e:
            # Handle failed operation details
            print(f"Operation failed: {e}")
        except PyMongoError as e:
            # Handle any other PyMongo errors
            print(f"An error occurred while querying: {e}")

    @classmethod
    def close_connection(cls):
        if cls._client is not None:
            cls._client.close()
            cls._client = None