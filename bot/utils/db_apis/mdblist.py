import asyncio
from functools import wraps
import json
import os
import pickle
import sys
import aiohttp
import urllib.parse

import cv2
import redis
import numpy as np
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.http_client import HttpClient


# TODO: move to config.json
MDBLIST_API_KEY = "uwk2jbhy7acivnyzpq44hh70y"


def cache_invalidation_on_new_data(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        result = await func(self, *args, **kwargs)
        self.clear_cache()
        return result
    return wrapper



class MDBList():
    def __init__(self, api_key=MDBLIST_API_KEY, redis_host='localhost', redis_port=6379, redis_db=10):
        self.api_key = api_key
        self.url = "https://mdblist.com/api/?apikey=" + self.api_key
        self.redis = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        self.colors_cache = redis.Redis(host=redis_host, port=redis_port, db=redis_db + 1)
        self.extract_cache = redis.Redis(host=redis_host, port=redis_port, db=redis_db + 2)
        # self.colors_cache = aioredis.create_from_pool(aioredis.ConnectionsPool.from_url(f"redis://localhost:6379/11"))/
        self.client: HttpClient = HttpClient()
    
    # @cache_invalidation_on_new_data
    async def search_movie(self, query: str) -> dict:
        encoded_query = urllib.parse.quote(query)
        url = self.url + "&m=movie&s=" + encoded_query
        cached_data = self.redis.get(url)
        if cached_data:
            return json.loads(cached_data)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                self.redis.set(url, json.dumps(data))
                return data
    
    # @cache_invalidation_on_new_data
    async def search_tv_show(self, query: str) -> dict:
        encoded_query = urllib.parse.quote(query)
        url = self.url + "&m=show&s=" + encoded_query
        cached_data = self.redis.get(url)
        if cached_data:
            return json.loads(cached_data)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                self.redis.set(url, json.dumps(data))
                return data
    
    # @cache_invalidation_on_new_data
    async def get_details(self, id_type: str, id_value: str) -> dict:
        url = self.url + f"&{id_type}={id_value}"
        cached_data = self.redis.get(url)
        if cached_data:
            return json.loads(cached_data)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                self.redis.set(url, json.dumps(data))
                return data
    
    def median_cut_quantization(self, image, num_colors: int = 1):
        lab_image = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        pixels = lab_image.reshape((-1, 3))
        quantized_pixels, buckets = [], [pixels]
        while len(quantized_pixels) < num_colors:
            new_buckets = []
            for bucket in buckets:
                ranges = [np.max(bucket[:, i]) - np.min(bucket[:, i]) for i in range(3)]
                max_range_channel = np.argmax(ranges)
                sorted_bucket = bucket[bucket[:, max_range_channel].argsort()]
                median_idx = len(sorted_bucket) // 2
                new_buckets.append(sorted_bucket[:median_idx])
                new_buckets.append(sorted_bucket[median_idx:])
            buckets = new_buckets
            for bucket in buckets:
                dominant_color = np.mean(bucket, axis=0)
                quantized_pixels.append(np.round(dominant_color).astype(np.uint8))
        return quantized_pixels[:num_colors]
    
    async def get_dominant_colors(self, id: str, image_url: str, num_colors: int = 1):
        cache_key = f"dominant_colors:{id}"
        cached_result = self.colors_cache.hget(cache_key, "colors")
        if cached_result:
            return pickle.loads(cached_result)
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(image_url)) as response:
                    image_data = await response.read()
                    image = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
                    image = cv2.resize(image, (150, 150))
                    median_cut_quantization = self.median_cut_quantization(image, num_colors)
                    self.colors_cache.hset(cache_key, "colors", pickle.dumps(median_cut_quantization))
                    return median_cut_quantization
    
    async def extract_details(self, details: dict, id: str, skip_dominant_colors: bool = False) -> dict:
        cache_key = f"extract_details:{id}"
        # print(f"Cache key: {cache_key}")
        cached_result = self.extract_cache.get(cache_key)
        # print(f"Cached result: {cached_result}")
        if cached_result:
            print("Retrieved from cache")
            return pickle.loads(cached_result)
        else:
            print("Not retrieved from cache")
            extracted = {
                "poster": details.get("poster", ""),
                "score_average": details.get("score_average", 0),
                "type": details.get("type", ""),
                "description": details.get("description", ""),
                "runtime": details.get("runtime", 0),
                "title": details.get("title", ""),
                "year": details.get("year", 0),
                "released": details.get("released", ""),
                "most_dominant_colors": [] if skip_dominant_colors else await self.get_dominant_colors(id, details.get("poster", ""), num_colors=3)
            }
            self.extract_cache.set(cache_key, pickle.dumps(extracted))
            print("Stored in cache")
            return extracted
    
    def clear_cache(self):
        self.redis.flushdb()


async def main():
    mdblist = MDBList()
    title = "The Avengers"
    movie_details = await mdblist.search_movie(title)
    results = movie_details.get("search")
    print(f"Results: {results[0]['id']}")
    details = await mdblist.get_details("i", results[0]['id'])
    extracted = await mdblist.extract_details(details, results[0]['id'])
    print(extracted)
    # tv_show_id = "tt21975436"
    # tv_show_details = await mdblist.get_details("i", tv_show_id)
    # import time
    # start_time = time.time()
    # details = await mdblist.extract_details(tv_show_details, tv_show_id)
    # print("Time taken:", time.time() - start_time)
    # print(details)
    # mdblist.clear_cache()

if __name__ == '__main__':
    asyncio.run(main())