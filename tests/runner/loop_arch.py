"""Test-only architectures. A plain Python loop, deliberately not a StateGraph (research R14)."""

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from apl.kit import Kit


def play(kit: Kit) -> None:
    model = kit.model.bind_tools(kit.tools)
    messages: list[BaseMessage] = [SystemMessage(kit.base_prompt), HumanMessage(kit.start)]
    while True:
        reply = model.invoke(messages)
        if not reply.tool_calls:
            return
        messages.append(reply)
        messages += kit.tool_node({"messages": messages})["messages"]


def crash(kit: Kit) -> None:
    raise ValueError("boom")
