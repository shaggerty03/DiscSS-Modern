import aiohttp

class HttpClient:
    def __init__(self) -> None:
        self.base_url = "http://localhost:3000"
    
    async def get(self, endpoint: str) -> aiohttp.ClientResponse:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/{endpoint}") as response:
                return { "status": response.status, "data": await response.json() }
    
    async def post(self, endpoint: str, data: dict) -> aiohttp.ClientResponse:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/{endpoint}", json=data) as response:
                if response.content_type == 'application/json':
                    data = await response.json()
                    print(f"Response: {data}")
                    return {"status": response.status, "data": await response.json()}
                else:
                    print(f"Unexpected content type: {response.content_type}, {await response.text()}")
                    raise ValueError(f"Unexpected content type: {response.content_type}")