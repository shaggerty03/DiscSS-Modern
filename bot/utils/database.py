from datetime import datetime
from dateutil.relativedelta import relativedelta
from functools import lru_cache, wraps
try:
    import logutils
except ImportError:
    from utils import logutils
import redis

logger = logutils.CustomLogger(__name__)

def cache_invalidation_on_user_change(func):
    @wraps(func)
    def wrapper(self, user_id, *args, **kwargs):
        result = func(self, user_id, *args, **kwargs)
        self.get_user.cache_clear()
        return result
    return wrapper

class RedisDB:
    def __init__(self, db=0):
        self.redis = redis.StrictRedis(connection_pool=redis.ConnectionPool(host='localhost', port=6379, db=db))

    @cache_invalidation_on_user_change
    def set_user(self, user_id, username, reason, proof_link, folder_id):
        """
        Sets the user information in a hash with fields for username, reason, proof link, and folder ID.
        """
        try:
            self.redis.hset(user_id, mapping={
                "username": username,
                "reason": reason,
                "proof_link": proof_link,
                "folder_id": folder_id
            })
        except redis.RedisError as e:
            logger.error(f"Error setting user {user_id} in the database: {e}")

    @lru_cache(maxsize=128)
    def get_user(self, user_id):
        """
        Retrieves all fields for a given user_id as a dictionary.
        """
        try:
            user_data = self.redis.hgetall(user_id)
            return {k.decode('utf-8'): v.decode('utf-8') for k, v in user_data.items()}
        except redis.RedisError as e:
            logger.error(f"Error getting user {user_id} from the database: {e}")
            return {}

    @cache_invalidation_on_user_change
    def delete_user(self, user_id):
        """
        Deletes a user entry by user_id.
        """
        try:
            self.redis.delete(user_id)
        except redis.RedisError as e:
            logger.error(f"Error deleting user {user_id} from the database: {e}")

    def list_all_users(self):
        """
        Lists all user_ids in the database.
        """
        try:
            return [key.decode('utf-8') for key in self.redis.scan_iter("*")]
        except redis.RedisError as e:
            logger.error(f"Error listing all users from the database: {e}")
            return []

    def list_all_users_info(self):
        """
        Lists all users and their associated information from the database.
        """
        users = self.list_all_users()
        all_user_data = {}
        try:
            with self.redis.pipeline() as pipeline:
                for user_id in users:
                    pipeline.hgetall(user_id)
                results = pipeline.execute()
                
                for user_id, user_data in zip(users, results):
                    all_user_data[user_id] = {k.decode('utf-8'): v.decode('utf-8') for k, v in user_data.items()}
        except redis.RedisError as e:
            logger.error(f"Error listing all users and their information from the database: {e}")
        return all_user_data

    def search_users(self, pattern):
        """
        Searches for users by matching a pattern in the username field.
        """
        matched_data = []
        try:
            users = self.list_all_users()
            for user_id in users:
                username = self.redis.hget(user_id, "username").decode('utf-8')
                if pattern.lower() in username.lower():
                    user_data = self.get_user(user_id)
                    matched_data.append((user_id, user_data))
        except redis.RedisError as e:
            logger.error(f"Error searching for users in the database: {e}")
        return matched_data
    
    def record_sync_details(self, guild_id, channel_id, count):
        """
        Records details of a sync operation to a guild channel.
        """
        try:
            self.redis.hset(f"sync_details:{guild_id}", mapping={
                "channel_id": channel_id,
                "count": count
            })
        except redis.RedisError as e:
            logger.error(f"Error recording sync details for guild {guild_id} in the database: {e}")
            
    def get_sync_details(self, guild_id):
        try:
            details = self.redis.hgetall(f"sync_details:{guild_id}")
            if details:
                return {k.decode('utf-8'): v.decode('utf-8') for k, v in details.items()}
            return {}
        except redis.RedisError as e:
            logger.error(f"Error getting sync details for guild {guild_id} from the database: {e}")
            return {}
    
    def set_last_sync_details(self, guild_id, sync_hash):
        """
        Records the last sync hash for a guild.
        """
        try:
            self.redis.hset("last_sync_hash", guild_id, sync_hash)
        except redis.RedisError as e:
            logger.error(f"Error setting last sync hash for guild {guild_id}: {e}")

    def get_last_sync_hash(self, guild_id):
        """
        Retrieves the last sync hash for a guild.
        """
        try:
            hash_bytes = self.redis.hget("last_sync_hash", guild_id)
            if hash_bytes is not None:
                return hash_bytes.decode('utf-8')
            return None
        except redis.RedisError as e:
            logger.error(f"Error getting last sync hash for guild {guild_id}: {e}")
            return None
        
    def list_all_sync_hashes(self):
        """
        Lists all guilds and their last sync hashes.
        """
        try:
            return {k.decode('utf-8'): v.decode('utf-8') for k, v in self.redis.hgetall("last_sync_hash").items()}
        except redis.RedisError as e:
            logger.error(f"Error listing all sync hashes from the database: {e}")
            return {}
        
    def list_all_sync_details(self):
        """
        Lists all guilds and their sync details.
        """
        try:
            return {k.decode('utf-8'): {k.decode('utf-8'): v.decode('utf-8') for k, v in v.items()} for k, v in self.redis.hgetall("sync_details").items()}
        except redis.RedisError as e:
            logger.error(f"Error listing all sync details from the database: {e}")
            return {}
        
    def check_if_guild_synced(self, guild_id, current_sync_hash):
        """
        Checks if a guild has already been synced with the current sync hash.
        """
        # Check if guild_id is in the database as an entry (sync_details:guild_id)
        if not self.redis.exists(f"sync_details:{guild_id}"):
            return False
        last_sync_hash = self.get_last_sync_hash(guild_id)
        return last_sync_hash == current_sync_hash

    def exists(self, user_id):
        """
        Checks if a user entry exists in the database.
        """
        try:
            return self.redis.exists(user_id)
        except redis.RedisError as e:
            logger.error(f"Error checking if user {user_id} exists in the database: {e}")
            return False

    def flush_db(self):
        """
        Clears the entire database, removing all keys and data.
        """
        try:
            self.redis.flushdb()
        except redis.RedisError as e:
            logger.error(f"Error flushing the database: {e}")
    
    def set_channel(self, guild_id, channel_id):
        """
        Sets the channel where the suggestions will be sent.
        """
        try:
            self.redis.hset("suggestions_channels", guild_id, channel_id)
        except redis.RedisError as e:
            logger.error(f"Error setting suggestions channel for guild {guild_id}: {e}")
    
    def get_channel(self, guild_id):
        """
        Gets the channel where the suggestions will be sent.
        """
        try:
            channel_id = self.redis.hget("suggestions_channels", guild_id)
            if channel_id:
                return channel_id.decode('utf-8')
            return None
        except redis.RedisError as e:
            logger.error(f"Error getting suggestions channel for guild {guild_id}: {e}")
            return None
    
    def delete_channel(self, guild_id):
        """
        Deletes the suggestions channel for a guild.
        """
        try:
            self.redis.hdel("suggestions_channels", guild_id)
        except redis.RedisError as e:
            logger.error(f"Error deleting suggestions channel for guild {guild_id}: {e}")
    
    def list_all_channels(self):
        """
        Lists all guilds and their suggestions channels.
        """
        try:
            return {k.decode('utf-8'): v.decode('utf-8') for k, v in self.redis.hgetall("suggestions_channels").items()}
        except redis.RedisError as e:
            logger.error(f"Error listing all suggestions channels from the database: {e}")
            return {}
    
    def increment_suggestions(self, user_id):
        user_id = str(user_id)
        current_month = datetime.now().strftime("%Y-%m")
        key = f"suggestions:{user_id}:{current_month}"
        try:
            new_value = self.redis.incrby(name=key, amount=1)
            year, month = int(current_month[:4]), int(current_month[5:])
            self.redis.expireat(key, int(datetime(year, month, 1).timestamp()))
            logger.info(f"New suggestion count for user {user_id}: {new_value} (type: {type(new_value)}, {type(str(new_value))}, {new_value})")
        except redis.RedisError as e:
            logger.error(f"Error incrementing suggestions for user {user_id}: {e}")
    
    def clear_all_suggestions(self):
        try:
            keys = self.redis.keys("suggestions:*")
            for key in keys:
                self.redis.delete(key)
        except redis.RedisError as e:
            logger.error(f"Error clearing all suggestions: {e}")

    def get_suggestions(self, user_id):
        current_month = datetime.now().strftime("%Y-%m")
        key = f"suggestions:{user_id}:{current_month}"
        try:
            return int(self.redis.get(key) or 0)
        except redis.RedisError as e:
            logger.error(f"Error getting suggestions for user {user_id}: {e}")
            return None
    
    def list_suggestions(self, user_id):
        current_date = datetime.now()
        keys = []
        for i in range(12):
            date = current_date - relativedelta(months=i)
            keys.append(f"suggestions:{user_id}:{date.strftime('%Y-%m')}")
        try:
            return {k: int(self.redis.get(k) or 0) for k in keys}
        except redis.RedisError as e:
            logger.error(f"Error listing suggestions for user {user_id}: {e}")
            return {}
    
    def list_current_month_suggestions(self, user_id):
        current_date = datetime.now()
        current_month_key = f"suggestions:{user_id}:{current_date.strftime('%Y-%m')}"
        try:
            return {current_month_key: int(self.redis.get(current_month_key) or 0)}
        except redis.RedisError as e:
            logger.error(f"Error listing suggestions for user {user_id}: {e}")
            return {}
    
    def clear_suggestions(self, user_id, count=None):
        try:
            current_suggestions = self.get_suggestions(user_id)
            if count is None: new_suggestions = 0
            else: new_suggestions = max(0, current_suggestions - count)
            self.redis.set(f"suggestions:{user_id}:{datetime.now().strftime('%Y-%m')}", new_suggestions)
        except redis.RedisError as e:
            logger.error(f"Error clearing suggestions for user {user_id}: {e}")
    
    def add_to_whitelist(self, user_id):
        try:
            self.redis.sadd("whitelist", user_id)
        except redis.RedisError as e:
            logger.error(f"Error adding user {user_id} to the whitelist: {e}")
    
    def remove_from_whitelistt(self, user_id):
        try:
            self.redis.srem("whitelist", user_id)
        except redis.RedisError as e:
            logger.error(f"Error removing user {user_id} from the whitelist: {e}")
    
    def is_whitelisted(self, user_id):
        try:
            return bool(self.redis.sismember("whitelist", user_id))
            # return self.redis.sismember("whitelist", user_id)
        except redis.RedisError as e:
            logger.error(f"Error checking if user {user_id} is whitelisted: {e}")
            return False
    
    def list_whitelist(self):
        try:
            return [user_id.decode('utf-8') for user_id in self.redis.smembers("whitelist")]
        except redis.RedisError as e:
            logger.error(f"Error listing whitelist users: {e}")
            return set()


if __name__ == '__main__':
    r = RedisDB(db=16)
    r.clear_all_suggestions()