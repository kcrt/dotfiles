#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from langchain_openai import ChatOpenAI
from browser_use import Agent
import asyncio
import sys
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
    print("Success!" if result.is_done() else "Failed!")
    print(result.final_result())

asyncio.run(main())
