import datetime
import uuid
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, PyMongoError

class MongoDBService:
    _client = None
    _backup_collection = "snapshots"

    @classmethod
    def _get_client(cls, db_url, client=None):
        if cls._client is None:
            if client is not None:
                cls._client = client
            else:
                try:
                    cls._client = MongoClient(db_url)
                    # You might want to add more robust connection handling and setup here
                except ConnectionFailure as e:
                    print(f"Could not connect to server: {e}")
        return cls._client
    
    def __init__(self, db_url, db_name, client=None):
        """
        Initialize the MongoDBService with the specified database URL and database name.

        :param db_url: URL for the MongoDB database.
        :param db_name: Name of the database to interact with.
        """
        self.db_client = self._get_client(db_url, client=client)
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
            print(f"Operation failed in query: {e}")
        except PyMongoError as e:
            # Handle any other PyMongo errors
            print(f"An error occurred while query: {e}")

    def insert_one(self, collection, document):
        try:
            if self.db is None:
                raise OperationFailure("Database not accessible")
            
            coll = self.db[collection]
            return coll.insert_one(document)

        except OperationFailure as e:
            # Handle failed operation details
            print(f"Operation failed in insert_one: {e}")
        except PyMongoError as e:
            # Handle any other PyMongo errors
            print(f"An error occurred while insert_one: {e}")

    def replace_one(self, collection, document, filter_dict, upsert = False):
        try:
            if self.db is None:
                raise OperationFailure("Database not accessible")
            coll = self.db[collection]
            return coll.replace_one(filter_dict, document, upsert)

        except OperationFailure as e:
            # Handle failed operation details
            print(f"Operation failed in replace_one: {e}")
        except PyMongoError as e:
            # Handle any other PyMongo errors
            print(f"An error occurred in replace_one: {e}")


    def delete_many(self, collection, filter_dict=None):
        if filter_dict is None:
            filter_dict = {}

        try:
            if self.db is None:
                raise OperationFailure("Database not accessible")
            
            coll = self.db[collection]
            return coll.delete_many(filter_dict)

        except OperationFailure as e:
            # Handle failed operation details
            print(f"Operation failed: {e}")
        except PyMongoError as e:
            # Handle any other PyMongo errors
            print(f"An error occurred in delete_many: {e}")
    
    def snapshot(self, snapshot_collection, collections_to_backup, description = "", start_time = None):
        try:
            collections = {}
            for col in collections_to_backup:
                documents = self.query(col)
                collections[col] = documents

            now = datetime.datetime.now()
            timestamp = now.timestamp()
            snapshot = {
                "id": str(uuid.uuid4()),
                "timestamp": timestamp,
                "since": start_time,
                "description": description,
                "collections": collections 
            }

            return self.insert_one(snapshot_collection, snapshot)
            
        except OperationFailure as e:
            # Handle failed operation details
            print(f"Operation failed during snapshot: {e}")
            return None
        except PyMongoError as e:
            # Handle any other PyMongo errors
            print(f"An error occurred in snapshot: {e}")
            return None



    @classmethod
    def close_connection(cls):
        if cls._client is not None:
            cls._client.close()
            cls._client = None