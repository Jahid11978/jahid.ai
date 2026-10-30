#!/usr/bin/env python3
from __future__ import annotations
import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from backend.agent_fabric import Agent,AgentGroup,AgentRegistry,Scheduler,Governor,Task

def demo():
    """Run a local Agent Fabric task and print its result."""
    registry=AgentRegistry()
    registry.register_agent(Agent("planner-1","Planner",frozenset({"plan"}),max_concurrency=2))
    registry.register_agent(Agent("coder-1","Coder",frozenset({"code"})))
    registry.register_group(AgentGroup("core","Core",("planner-1","coder-1")))
    scheduler=Scheduler(registry,Governor())
    result=scheduler.dispatch(Task("demo-1","demo","code",{"value":40}),lambda t:{"value":t.input["value"]+2},"core")
    print({"state":result.state.value,"output":dict(result.output),"worker_id":result.worker_id})

def main():
    """Parse the command-line arguments and run the requested command."""
    parser=argparse.ArgumentParser(prog="jahids")
    parser.add_argument("command",choices=["agent-demo"])
    args=parser.parse_args()
    if args.command=="agent-demo": demo()

if __name__=="__main__": main()
