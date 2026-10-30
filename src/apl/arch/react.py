"""A1 ReAct: the model calls tools in a loop; its only memory is the message history."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from apl.kit import Kit


def play(kit: Kit) -> None:
    model = kit.model.bind_tools(kit.tools)

    def agent(state: MessagesState) -> dict[str, list[AIMessage]]:
        return {"messages": [model.invoke(state["messages"])]}

    def route(state: MessagesState) -> str:
        last = state["messages"][-1]
        # Unparsable calls go to the tools too: they cost a step and get an error back.
        has_calls = isinstance(last, AIMessage) and (last.tool_calls or last.invalid_tool_calls)
        return "tools" if has_calls else END

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", kit.tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route)
    graph.add_edge("tools", "agent")
    graph.compile().invoke(
        {"messages": [SystemMessage(kit.base_prompt), HumanMessage(kit.start)]},
        config={"recursion_limit": kit.recursion_limit},
    )
