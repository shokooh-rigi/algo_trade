import redis
import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class RedisHandler:
    def __init__(
            self,
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB
    ):
        """
        Initialize Redis connection.

        :param host: The Redis server hostname.
        :param port: The Redis server port.
        :param db: The Redis database index.
        """
        try:
            self.client = redis.StrictRedis(
                host=host,
                port=port,
                db=db,
                decode_responses=True
            )
            self.client.ping()
        except redis.ConnectionError as e:
            raise Exception(f"Unable to connect to Redis at {host}:{port} - {e}")

    def store(self, key, value):
        """
        Store an object in Redis.

        :param key: The key to store the object under.
        :param value: The value (object) to store, converted to JSON if necessary.
        """
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        try:
            self.client.set(key, value)
            logger.info(f"Key '{key}' stored successfully.")
            print(f"Key '{key}' stored successfully.")
        except Exception as e:
            logger.info(f"Failed to store key '{key}': {e}")
            print(f"Failed to store key '{key}': {e}")

    def fetch(self, key):
        """
        Fetch an object from Redis.

        :param key: The key of the object to retrieve.
        :return: The object (decoded from JSON if applicable).
        """
        if not self.client.exists(key):
            raise KeyError(f"Key '{key}' does not exist in Redis.")
        value = self.client.get(key)
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return value

    def update(self, key, value):
        """
        Update an existing object in Redis.

        :param key: The key of the object to update.
        :param value: The new value to store (converted to JSON if necessary).
        """
        if self.client.exists(key):
            self.store(key, value)
        else:
            raise KeyError(f"Key '{key}' does not exist in Redis.")

    def delete(self, key):
        """
        Delete an object from Redis.

        :param key: The key of the object to delete.
        :return: The number of keys deleted (0 or 1).
        """
        return self.client.delete(key)

    def ping(self):
        """
        Check if the Redis server is reachable.

        :return: True if reachable, False otherwise.
        """
        try:
            return self.client.ping()
        except redis.ConnectionError:
            return False

