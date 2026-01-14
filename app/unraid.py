"""Unraid GraphQL API client for Docker container management."""

import httpx
from dataclasses import dataclass


@dataclass
class ContainerStatus:
    name: str
    state: str  # RUNNING, EXITED, etc.


class UnraidClient:
    """Client for Unraid's GraphQL API."""

    def __init__(self, url: str, api_key: str):
        self.graphql_url = f"{url.rstrip('/')}/graphql"
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }

    async def _query(self, query: str) -> dict:
        """Execute a GraphQL query."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.graphql_url,
                headers=self.headers,
                json={"query": query},
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_container_status(self, container_name: str) -> ContainerStatus | None:
        """Get the status of a specific container."""
        query = "{ docker { containers { names state } } }"
        result = await self._query(query)

        containers = result.get("data", {}).get("docker", {}).get("containers", [])
        for container in containers:
            names = container.get("names", [])
            # Names include leading slash, e.g., ["/itzg-minecraft-server"]
            if f"/{container_name}" in names or container_name in names:
                return ContainerStatus(
                    name=container_name,
                    state=container.get("state", "UNKNOWN"),
                )
        return None

    async def start_container(self, container_name: str) -> bool:
        """Start a container. Returns True if successful."""
        query = f'mutation {{ docker {{ start(id: "{container_name}") {{ names }} }} }}'
        try:
            await self._query(query)
        except Exception:
            pass  # The mutation works but returns an error (Unraid API bug)

        # Verify the container started
        status = await self.get_container_status(container_name)
        return status is not None and status.state == "RUNNING"

    async def stop_container(self, container_name: str) -> bool:
        """Stop a container. Returns True if successful."""
        query = f'mutation {{ docker {{ stop(id: "{container_name}") {{ names }} }} }}'
        try:
            await self._query(query)
        except Exception:
            pass  # The mutation works but returns an error (Unraid API bug)

        # Verify the container stopped
        status = await self.get_container_status(container_name)
        return status is not None and status.state == "EXITED"

    async def restart_container(self, container_name: str) -> bool:
        """Restart a container (stop then start). Returns True if successful."""
        # Stop first
        await self.stop_container(container_name)

        # Give it a moment
        import asyncio
        await asyncio.sleep(2)

        # Start
        return await self.start_container(container_name)
