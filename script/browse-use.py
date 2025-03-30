#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from langchain_openai import ChatOpenAI
from browser_use import Agent
import asyncio
import argparse
import json

llm = ChatOpenAI(model="gpt-4o")


async def main():
    parser = argparse.ArgumentParser(
        description='Process a prompt for the agent.')
    parser.add_argument('prompt', type=str, help='The prompt to process')
    args = parser.parse_args()

    agent = Agent(
        task=args.prompt,
        llm=llm,
    )
    result = await agent.run()
    print(json.dumps(result, indent=4, ensure_ascii=False))

asyncio.run(main())
