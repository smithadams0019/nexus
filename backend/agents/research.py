"""ResearchAgent — provides real-world grounding via Gemini with Google Search."""

import json
import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

FACT_CHECK_PROMPT = """You are a fact-checker. A user has made the following claim:

"{claim}"

Using the search results available to you, determine whether this claim is true, false, or unverifiable.
Respond ONLY with valid JSON:
{{
  "verified": true or false,
  "explanation": "brief explanation of your finding"
}}"""

PRICE_COMPARE_PROMPT = """Search for current prices of the following product and provide a comparison:

"{product_description}"

Respond ONLY with valid JSON:
{{
  "results": [
    {{"name": "product name / variant", "price": "price as string with currency", "source": "retailer or source name"}},
    ...
  ]
}}

Include up to 5 results. If no pricing information is found, return {{"results": []}}."""


class ResearchAgent:
    """Performs grounded research using Gemini 2.0 Flash with Google Search."""

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        self._client = genai.Client(api_key=api_key)
        self._model = "gemini-2.5-flash"
        self._search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )

    def _extract_sources(self, response) -> list[str]:
        """Extract source URLs from grounding metadata in the response."""
        sources: list[str] = []
        try:
            candidate = response.candidates[0]
            grounding_meta = getattr(candidate, "grounding_metadata", None)
            if grounding_meta is None:
                return sources

            # grounding_chunks contain web references
            chunks = getattr(grounding_meta, "grounding_chunks", None)
            if chunks:
                for chunk in chunks:
                    web = getattr(chunk, "web", None)
                    if web:
                        uri = getattr(web, "uri", None)
                        if uri:
                            sources.append(uri)

            # Also check grounding_supports for additional URIs
            supports = getattr(grounding_meta, "grounding_supports", None)
            if supports:
                for support in supports:
                    segment_sources = getattr(support, "grounding_chunk_indices", None)
                    # Already captured via chunks above
                    _ = segment_sources

            # Fallback: search_entry_point may contain rendered HTML with links
            if not sources:
                entry_point = getattr(grounding_meta, "search_entry_point", None)
                if entry_point:
                    rendered = getattr(entry_point, "rendered_content", None)
                    if rendered:
                        # Extract URLs from rendered HTML (best-effort)
                        import re

                        urls = re.findall(r'href="(https?://[^"]+)"', rendered)
                        sources.extend(urls[:5])

        except (IndexError, AttributeError) as exc:
            logger.debug("Could not extract sources from grounding metadata: %s", exc)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for url in sources:
            if url not in seen:
                seen.add(url)
                unique.append(url)
        return unique

    async def search(self, query: str) -> dict:
        """Perform a grounded search using Gemini + Google Search.

        Args:
            query: The search query.

        Returns:
            Dict with keys: answer (str), sources (list[str]).
        """
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[self._search_tool],
                    temperature=0.2,
                    max_output_tokens=2048,
                ),
            )

            answer = response.text.strip() if response.text else ""
            sources = self._extract_sources(response)

            return {"answer": answer, "sources": sources}

        except Exception as exc:
            logger.error("ResearchAgent.search failed: %s", exc, exc_info=True)
            return {"answer": f"Search failed: {exc}", "sources": []}

    async def fact_check(self, claim: str) -> dict:
        """Fact-check a claim using grounded search.

        Args:
            claim: The claim to verify.

        Returns:
            Dict with keys: verified (bool), explanation (str), sources (list[str]).
        """
        prompt = FACT_CHECK_PROMPT.format(claim=claim)

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[self._search_tool],
                    temperature=0.1,
                    max_output_tokens=1024,
                ),
            )

            sources = self._extract_sources(response)
            text = response.text.strip() if response.text else ""

            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            try:
                result = json.loads(text)
                return {
                    "verified": bool(result.get("verified", False)),
                    "explanation": result.get("explanation", ""),
                    "sources": sources,
                }
            except json.JSONDecodeError:
                logger.warning("Fact-check response was not valid JSON: %s", text[:200])
                return {
                    "verified": False,
                    "explanation": text,
                    "sources": sources,
                }

        except Exception as exc:
            logger.error("ResearchAgent.fact_check failed: %s", exc, exc_info=True)
            return {
                "verified": False,
                "explanation": f"Fact-check failed: {exc}",
                "sources": [],
            }

    async def compare_prices(self, product_description: str) -> dict:
        """Search for and compare prices of a product.

        Args:
            product_description: Description of the product to price-check.

        Returns:
            Dict with key: results (list of dicts with name, price, source).
        """
        prompt = PRICE_COMPARE_PROMPT.format(product_description=product_description)

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[self._search_tool],
                    temperature=0.2,
                    max_output_tokens=2048,
                ),
            )

            text = response.text.strip() if response.text else ""

            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            try:
                result = json.loads(text)
                raw_results = result.get("results", [])
                # Normalize each entry
                normalized: list[dict] = []
                for item in raw_results:
                    normalized.append({
                        "name": str(item.get("name", "")),
                        "price": str(item.get("price", "")),
                        "source": str(item.get("source", "")),
                    })
                return {"results": normalized}
            except json.JSONDecodeError:
                logger.warning(
                    "Price comparison response was not valid JSON: %s", text[:200]
                )
                return {"results": []}

        except Exception as exc:
            logger.error(
                "ResearchAgent.compare_prices failed: %s", exc, exc_info=True
            )
            return {"results": []}
